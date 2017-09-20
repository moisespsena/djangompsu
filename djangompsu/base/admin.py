# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy

import six
from django.contrib import admin
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.utils import unquote, get_fields_from_path, flatten_fieldsets
from django.core.exceptions import PermissionDenied, FieldDoesNotExist
from django.db.models.fields.related import RelatedField
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import SimpleTemplateResponse
from django.utils.translation import ugettext_lazy as _
from modelclone.admin import ClonableModelAdminMix

from djangompsu.adminfilters import PolicyRelatedFieldListFilter
from djangompsu.policies import CHANGE, DELETE
from ..base.models import ModelWithPolicy
from ..utils import get_changelist_filters


class ModelAdminMix(object):
    add_fieldsets = None
    change_fieldsets = None
    default_fieldsets = ()
    add_exclude = ()
    change_exclude = ()
    add_inlines = []
    change_inlines = []
    default_inlines = []
    show_info_exclude = ()

    def get_add_fieldsets(self, request):
        return self.add_fieldsets or self.default_fieldsets

    def get_change_fieldsets(self, request):
        return self.change_fieldsets or self.default_fieldsets

    def get_fieldsets(self, request, obj=None):
        if not obj:
            fs = self.get_add_fieldsets(request)
        else:
            fs = self.get_change_fieldsets(request)

        if not fs:
            fs = super(ModelAdminMix, self).get_fieldsets(request, obj) or ()

        fs = expand_fs_fields(fs, {})

        return fs

    def post_store(self, request, obj):
        pass

    def response_change(self, request, obj):
        self.post_store(request, obj)
        return super(ModelAdminMix, self).response_change(request, obj)

    def response_add(self, request, obj, post_url_continue=None):
        self.post_store(request, obj)
        return super(ModelAdminMix, self).response_add(request, obj, post_url_continue)

    def get_add_exclude(self, request):
        return list(self.add_exclude)

    def get_change_exclude(self, request, obj):
        return list(self.change_exclude)

    def get_exclude(self, request, obj=None):
        exclude = list(self.exclude or ()) + list(
            self.get_add_exclude(request)
            if obj is None
            else
            self.get_change_exclude(request, obj)
        )
        return exclude

    def prepare_base_fields(self, form, request, obj=None):
        base_fields = form.base_fields

        for fname, field in base_fields.iteritems():
            if hasattr(field, 'queryset'):
                if hasattr(field.queryset.model, 'filter_objects_by_request'):
                    field.queryset = field.queryset.model.filter_objects_by_request(request, field.queryset)
                if hasattr(self.model, 'filter_formfield_by_request'):
                    field.queryset = self.model.filter_formfield_by_request(request, fname,
                                                                            getattr(self.model, fname, None),
                                                                            field, field.queryset)

    def get_form(self, request, obj=None, **kwargs):
        readonly = self.get_readonly_fields(request, obj)
        exclude = self.get_exclude(request, obj) + readonly
        kwargs['exclude'] = exclude
        ModelForm = super(ModelAdminMix, self).get_form(request, obj, **kwargs)
        self.prepare_base_fields(ModelForm, request, obj)
        return ModelForm

    def list_objects(self, request, extra_context=None):
        from django.contrib.admin.views.main import ERROR_FLAG

        list_display = self.get_list_display(request)
        list_display_links = self.get_list_display_links(request, list_display)
        list_filter = self.get_list_filter(request)
        search_fields = self.get_search_fields(request)

        # Check actions to see if any are available on this changelist
        actions = self.get_actions(request)
        if actions:
            # Add the action checkboxes if there are any actions available.
            list_display = ['action_checkbox'] + list(list_display)

        ChangeList = self.get_changelist(request)
        try:
            cl = ChangeList(request, self.model, list_display,
                            list_display_links, list_filter, self.date_hierarchy,
                            search_fields, self.list_select_related, self.list_per_page,
                            self.list_max_show_all, self.list_editable, self)
            return cl
        except IncorrectLookupParameters:
            # Wacky lookup parameters were given, so redirect to the main
            # changelist page, without parameters, and pass an 'invalid=1'
            # parameter via the query string. If wacky parameters were given
            # and the 'invalid=1' parameter was already in the query string,
            # something is screwed up with the database, so display an error
            # page.
            if ERROR_FLAG in request.GET.keys():
                return SimpleTemplateResponse('admin/invalid_setup.html', {
                    'title': _('Database error'),
                })
            return HttpResponseRedirect(request.path + '?' + ERROR_FLAG + '=1')

    def get_add_inlines(self, defaults, request):
        return defaults + self.add_inlines

    def get_change_inlines(self, defaults, request, obj):
        return defaults + self.change_inlines

    def get_default_inlines(self, request):
        return self.default_inlines

    def get_inlines(self, request, obj=None):
        inlines = (self.default_inlines + self.inlines)

        inlines = self.get_change_inlines(inlines, request, obj) \
            if obj \
            else self.get_add_inlines(inlines, request)
        return inlines

    def get_inline_instances(self, request, obj=None):
        inline_instances = []
        inlines = self.get_inlines(request, obj)

        for inline_class in inlines:
            inline = inline_class(self.model, self.admin_site)
            if request:
                if not (inline.has_add_permission(request) or
                            inline.has_change_permission(request, obj) or
                            inline.has_delete_permission(request, obj)):
                    continue
                if not inline.has_add_permission(request):
                    inline.max_num = 0
            inline_instances.append(inline)

        return inline_instances

    def get_changeform_initial_data(self, request):
        initial = super(ModelAdminMix, self).get_changeform_initial_data(
            request)
        filters = get_changelist_filters(request)

        for k in filters:
            if '__id__' in k:
                field_name = k.split('__', 2)[0]

                if field_name in initial:
                    continue
            elif k.endswith('__exact'):
                field_name = k.split('__', 2)[0]

                if field_name in initial:
                    continue
            else:
                continue

            try:
                self.model._meta.get_field(field_name)
                initial[field_name] = filters[k]
            except FieldDoesNotExist:
                continue

        return initial

    def get_readonly_fields(self, request, obj=None, super_=False):
        if obj and isinstance(obj, ModelWithPolicy):
            if not obj.has_perm(request.user, CHANGE):
                fields = flatten_fieldsets(self.get_fieldsets(request, obj))
                return fields
        return list(super(ModelAdminMix, self).get_readonly_fields(request, obj))

        # class Media:
        # js = ('mda/formutils.js',)


class ModelAdminBase(admin.ModelAdmin):
    pre_save_listeners = None
    pre_save_related_listeners = None
    post_clone_listeners = None
    clone_verbose_name = _('Duplicate')

    def __init__(self, *args, **kwargs):
        super(ModelAdminBase, self).__init__(*args, **kwargs)
        if self.list_filter:
            list_filter = list(self.list_filter)
            for i, f in enumerate(list_filter):
                if isinstance(f, six.string_types):
                    try:
                        field = get_fields_from_path(self.model, f)[-1]
                    except:
                        pass
                    else:
                        if isinstance(field, RelatedField):
                            if hasattr(field.related_model, 'filter_objects_by_request'):
                                list_filter[i] = (f, PolicyRelatedFieldListFilter)
            self.list_filter = list_filter
        self.init_listeners()

    def post_clone(self, request, original_obj, new_obj):
        for cb in self.post_clone_listeners:
            cb(request, original_obj, new_obj)

    def view_view(self, request, object_id, form_url='', extra_context=None):
        self.exclude = self.fieldsets

    def get_formsets_with_inlines(self, request, obj=None):
        for formset, inline in super(ModelAdminBase, self).get_formsets_with_inlines(request, obj):
            if isinstance(inline, ModelAdminMix):
                inline.exclude = inline.get_exclude(request, obj)

            self.prepare_base_fields(formset.form, request, obj)
            if hasattr(inline, 'prepare_formset'):
                inline.prepare_formset(formset, request, obj)
            yield formset, inline

    def init_listeners(self):
        self.pre_save_listeners = [] if self.pre_save_listeners is None else self.pre_save_listeners[:]
        self.pre_save_related_listeners = [] if self.pre_save_related_listeners is None \
            else self.pre_save_related_listeners[:]
        self.post_clone_listeners = [] if self.post_clone_listeners is None \
            else self.post_clone_listeners[:]

    def save_form(self, request, form, change):
        for cb in self.pre_save_listeners:
            cb(request, form, change)
        return super(ModelAdminBase, self).save_form(request, form, change)

    def save_related(self, request, form, formsets, change):
        for cb in self.pre_save_related_listeners:
            cb(request, form, formsets, change)
        return super(ModelAdminBase, self).save_related(request, form, formsets, change)

    def get_queryset(self, request):
        if hasattr(self.model, 'filter_objects_by_request'):
            return self.model.filter_objects_by_request(request, super(ModelAdminBase, self).get_queryset(request))
        return super(ModelAdminBase, self).get_queryset(request)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        if request.method == 'POST' and hasattr(self.model, 'has_perm'):
            if not get_object_or_404(self.model, pk=unquote(object_id)).has_perm(request.user, CHANGE):
                raise PermissionDenied

        return super(ModelAdminBase, self).change_view(request, object_id, form_url, extra_context)

    def delete_view(self, request, object_id, extra_context=None):
        if not get_object_or_404(self.model, pk=unquote(object_id)).has_perm(request.user, DELETE):
            raise PermissionDenied
        return super(ModelAdminBase, self).delete_view(request, object_id, extra_context=extra_context)

    def get_changelist(self, request, **kwargs):
        return super(ModelAdminBase, self).get_changelist(request, **kwargs)


class ModelAdmin(ModelAdminMix, ClonableModelAdminMix, ModelAdminBase):
    pass


class CreationInfoModelAdmin(ModelAdmin):
    add_exclude = ('created', 'created_by')

    def get_readonly_fields(self, request, obj=None):
        rlf = list(super(CreationInfoModelAdmin, self).get_readonly_fields(request, obj))
        if obj:
            rlf.extend(('created', 'created_by'))
        return rlf


class OwnedModelAdminMixin(ModelAdminMix):
    FIELDS_OF_CONTROL = ('created', 'created_by', 'updated', 'updated_by', 'owner')
    add_exclude = tuple(FIELDS_OF_CONTROL)
    change_exclude = ()
    exclude_control_fields = False

    @classmethod
    def set_owned_fields_force(cls, request, obj):
        model = obj.__class__
        if hasattr(model, 'created_by'):
            obj.created_by = request.user
        if hasattr(model, 'owner'):
            obj.owner = request.user
        if hasattr(model, 'updated_by'):
            obj.updated_by = request.user

    @classmethod
    def set_owned_fields(cls, model, request, obj):
        if obj._state.adding:
            if hasattr(model, 'created_by'):
                obj.created_by = request.user
            if hasattr(model, 'owner'):
                obj.owner = request.user
        if hasattr(model, 'updated_by'):
            obj.updated_by = request.user

    @classmethod
    def pre_save_set_owned_fields(cls, request, form, change):
        cls.set_owned_fields(form._meta.model, request, form.instance)

    @classmethod
    def pre_save_set_related_owned_fields(cls, request, form, formsets, change):
        for formset in formsets:
            for frm in formset.forms:
                cls.set_owned_fields(formset.model, request, frm.instance)

    def init_listeners(self):
        super(OwnedModelAdminMixin, self).init_listeners()
        self.pre_save_listeners.append(self.pre_save_set_owned_fields)
        self.pre_save_related_listeners.append(self.pre_save_set_related_owned_fields)

    def tweak_cloned_fields(self, fields):
        fields = super(OwnedModelAdminMixin, self).tweak_cloned_fields(fields)
        fields['owner'] = fields['created_by'] = fields['updated_by'] = None
        return fields

    def tweak_cloned_inline_fields(self, related_name, fields_list):
        fields_list = super(OwnedModelAdminMixin, self).tweak_cloned_inline_fields(related_name, fields_list)
        for fields in fields_list:
            fields['owner'] = fields['created_by'] = fields['updated_by'] = None
        return fields_list

    def get_change_fieldsets(self, request):
        fs = super(OwnedModelAdminMixin, self).get_change_fieldsets(request) or ()
        if not self.exclude_control_fields:
            fs = fs + ((_('Controle'), {
                'classes': ('collapse',),
                'fields': self.FIELDS_OF_CONTROL
            }),)
        return fs

    def get_exclude(self, request, obj=None):
        excludes = super(OwnedModelAdminMixin, self).get_exclude(request, obj)
        if self.exclude_control_fields:
            excludes += self.FIELDS_OF_CONTROL
        return excludes

    def get_readonly_fields(self, request, obj=None, super_=False):
        rlf = list(super(OwnedModelAdminMixin, self).get_readonly_fields(request, obj))
        if not self.exclude_control_fields:
            if obj:
                if not request.user.is_superuser and not 'owner' in rlf:
                    rlf.append('owner')

                rlf.extend(('created', 'updated', 'created_by', 'updated_by'))
        return rlf


class OwnedModelAdmin(OwnedModelAdminMixin, ClonableModelAdminMix, ModelAdminBase):
    pass


class CreationInfoInlineAdmin(admin.TabularInline):
    default_fieldsets = None
    exclude = ('created', 'created_by')


class TabularInline(ModelAdminMix, admin.TabularInline):
    default_fieldsets = None

    def __init__(self, *args, **kwargs):
        super(TabularInline, self).__init__(*args, **kwargs)


class OwnedTabularInline(OwnedModelAdminMixin, admin.TabularInline):
    exclude_control_fields = True

    def get_formset(self, request, obj=None, **kwargs):
        f = super(OwnedTabularInline, self).get_formset(request, obj, **kwargs)
        return f


class StackedInline(ModelAdminMix, admin.StackedInline):
    def __init__(self, *args, **kwargs):
        super(StackedInline, self).__init__(*args, **kwargs)

    def get_formset(self, request, obj=None, **kwargs):
        self.exclude = self.get_exclude(request, obj)
        self.fieldsets = self.get_fieldsets(request, obj)
        return super(StackedInline, self).get_formset(request, obj, **kwargs)


class OwnedStackedInline(StackedInline):
    exclude_control_fields = True


def expand_fs_fields(fs, items, inserts=None, cb=(lambda fds, key: fds), key=()):
    fs = list(fs[:])
    for k, v in items.iteritems():
        fs[k] = list(fs[k])
        fs[k][1] = copy.copy(fs[k][1])
        fs[k] = tuple(fs[k])

        if isinstance(v, dict):
            skey = key + (k,)
            fs[k][1]['fieldsets'] = expand_fs_fields(fs[1][k]['fieldsets'], v, inserts.get(skey), cb, skey)
        else:
            fields = v(fs[k][1]['fields']) if callable(v) else (fs[k][1]['fields'] + v)
            fs[k][1]['fields'] = cb(fields, key + (k,))

    if inserts:
        x = 0
        it = inserts.iteritems()
        for i, part in it:
            i += x
            fs.insert(i, part)
            x += i
    return tuple(fs)


def _test():
    fs = (
        (None, {'fields': ('a',)}),
        (None, {'fieldsets': (
            (None, {'fields': ('a',)}),
            (None, {'fields': ('a',)}),
        )}),
        (None, {'fields': ('r',)}),
        (None, {'fields': ('k',)}),
        (None, {'fields': ('g',)}),
    )
    new_fs = expand_fs_fields(fs, {
        0: ('x',),
        1: {
            1: ('c',),
        }},
                              {
                                  1: ((None, {'fields': ('z',)}),),
                                  3: ((None, {'fields': ('z1',)}),)
                              })
    # assert new_fs == (
    #    (None, {'fields': ('a','x')}),
    #    (None, {'fieldsets': (
    #        (None, {'fields': ('a',)}),
    #        (None, {'fields': ('a','c')}),
    #    )}),
    # )
    assert True


_test()


class OwnedSimpleNamedWithDesccriptionStackedInline(OwnedStackedInline):
    default_fieldsets = (
        (None, {'fields': ('nome', 'descricao')}),
    )


class OwnedSimpleNamedWithDesccriptionAdmin(OwnedModelAdmin):
    default_fieldsets = OwnedSimpleNamedWithDesccriptionStackedInline.default_fieldsets


class OwnedNamedWithDesccriptionStackedInline(OwnedStackedInline):
    default_fieldsets = OwnedSimpleNamedWithDesccriptionStackedInline.default_fieldsets + (
        (_('Descrição longa'), {
            'classes': ('collapse',),
            'fields': ('descricao_longa',)
        }),
    )


class OwnedNamedWithDescriptionAdmin(OwnedModelAdmin):
    default_fieldsets = OwnedNamedWithDesccriptionStackedInline.default_fieldsets
    search_fields = ['nome']
