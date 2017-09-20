import copy
import sys

from django import forms
from django.contrib.admin import utils
from django.contrib.admin.helpers import Fieldset, InlineFieldset, \
    InlineAdminForm, AdminForm
from django.contrib.admin.options import ModelAdmin
from django.conf.urls import patterns

old_flatten_fieldsets = utils.flatten_fieldsets


def expand_fs_fields(fs, items, inserts=None, cb=(lambda fds: fds)):
    fs = list(fs[:])
    for k, v in items.iteritems():
        fs[k] = list(fs[k])
        fs[k][1] = copy.copy(fs[k][1])
        fs[k] = tuple(fs[k])

        if isinstance(v, dict):
            fs[k][1]['fieldsets'] = expand_fs_fields(fs[1][k]['fieldsets'], v)
        else:
            fields = v(fs[k][1]['fields']) if callable(v) else (
                fs[k][1]['fields'] + v)
            fs[k][1]['fields'] = cb(fields)

    if inserts:
        x = 0
        it = inserts.iteritems()
        for i, part in it:
            i += x
            fs.insert(i, part)
            x += i
    return tuple(fs)


def filter_fields(fieldsets, exclude):
    new_fs = []
    for fs in fieldsets:
        options = fs[1]
        if 'fieldsets' in options:
            sub_fss = filter_fields(options['fieldsets'], exclude)

            if sub_fss:
                opts = copy.copy(options)
                options['fieldsets'] = sub_fss
                new_fs.append((fs[0], opts))
        else:
            fields = []
            for field in options['fields']:
                if isinstance(field, basestring):
                    if not field in exclude:
                        fields.append(field)
                else:
                    fds = []
                    for f in field:
                        if not f in exclude:
                            fds.append(f)
                    if fds:
                        fields.append(tuple(fds))

            if fields:
                opts = copy.copy(options)
                opts['fields'] = fields
                new_fs.append((fs[0], opts))
    return new_fs


def flatten_fieldsets(fieldsets):
    """Returns a list of field names from an admin fieldsets structure."""
    fields = fields_from_fieldsets(fieldsets)
    fields_names = []
    for field in fields:
        if isinstance(field, (list, tuple)):
            fields_names.extend(field)
        else:
            fields_names.append(field)
    return fields_names


sys.modules['django.contrib.admin.utils'].flatten_fieldsets = flatten_fieldsets
ModelAdmin.get_form.im_func.func_globals[
    'flatten_fieldsets'] = flatten_fieldsets


def change_inline_admin_form_init():
    cls = InlineAdminForm
    old_init = cls.__init__

    def __init__(self, *args, **kwargs):
        form = args[1]
        fieldsets = args[2]
        if form._meta.exclude:
            args = list(args)
            args[2] = filter_fields(fieldsets, form._meta.exclude)
        return old_init(self, *args, **kwargs)

    __init__.__old__ = old_init
    cls.__init__ = __init__


change_inline_admin_form_init()


def change_admin_form_iter():
    cls = AdminForm
    old = cls.__iter__

    def __iter__(*args, **kwargs):
        for fieldset in old(*args, **kwargs):
            if fieldset.fields:
                yield fieldset

    __iter__.__old__ = old
    cls.__iter__ = __iter__


change_admin_form_iter()

old_fieldset_init = Fieldset.__init__


def _my_fieldset_init(self, form, *args, **kwargs):
    readonly = kwargs.get('readonly_fields') or ()
    exclude = form._meta.exclude or ()
    kwargs['fields'] = filter(lambda _: not _ in exclude or _ in readonly,
                              kwargs.get('fields') or ())
    fieldsets = list(kwargs.pop('fieldsets', ()))
    old_fieldset_init(self, form, *args, **kwargs)
    self.fieldsets = fieldsets

    for i, (name, options) in enumerate(fieldsets):
        kw = {}
        kw.update(options)
        kw['name'] = name
        fieldsets[i] = Fieldset(form, **kw)


Fieldset.__init__ = _my_fieldset_init


def fields_from_fieldsets_(fieldsets, to):
    for fs in fieldsets:
        options = fs[1]
        if 'fieldsets' in options:
            fields_from_fieldsets_(options['fieldsets'], to)
        else:
            to.extend(utils.flatten(options['fields']))


def fields_from_fieldsets(fieldsets):
    to = []
    fields_from_fieldsets_(fieldsets, to)
    return to


def fields_from_fieldset(fieldset):
    return fields_from_fieldsets((fieldset,))


def url_base(model_admin):
    return '{0}_{1}'.format(model_admin.model._meta.app_label,
                            getattr(model_admin.model._meta, 'module_name',
                                    getattr(model_admin.model._meta,
                                            'model_name', '')))


def extend_urls(model_admin, *urls):
    prefix = url_base(model_admin)

    for url in urls:
        if getattr(url, 'name', None):
            url.name = '%s_%s' % (prefix, url.name)

    return patterns('', *urls)


MPSU_HIDDEN = 'mpsu_hidden'


class PrivateFieldsFormMixin(object):
    def __init__(self, *args, **kwargs):
        rl = d = None
        meta = self._meta
        fields = meta.fields
        lrl = []

        if hasattr(meta, 'mpsu_hidden_fields'):
            rl = meta.mpsu_hidden_fields

        if 'initial' in kwargs:
            self.private_load_initial_data(kwargs['initial'], lrl)

        elif not kwargs.get('instance') and args and rl:
            data = args[0]
            d = {}

            for k in rl:
                v = data[k + "_" + MPSU_HIDDEN][0]
                if k in fields:
                    data[k] = v
                else:
                    d[k] = v

            self.private_load_data(d)
            data.update(d)

        super(PrivateFieldsFormMixin, self).__init__(*args, **kwargs)

        obj = self.instance
        initial = self.initial
        model = meta.model

        if d:
            for name in d:
                if hasattr(model, name):
                    setattr(obj, name, d[name])

        elif lrl:
            for name in lrl:
                setattr(obj, name, initial[name])

        if rl:
            sufix = '_' + MPSU_HIDDEN

            for name, options in rl.iteritems():
                d = {'args': (), 'kwargs': {'widget': forms.HiddenInput},
                     'cls': forms.CharField}

                if isinstance(options, dict) and 'value' in options:
                    d.update(options)
                else:
                    d['value'] = options

                f = d['cls'](*d['args'], **d['kwargs'])
                name = name + sufix
                self.initial[name] = d['value']
                self.fields[name] = f

    def private_load_static_data(self, data):
        pass

    def private_load_initial_data(self, data, rl):
        self.private_load_static_data(data)

    def private_load_data(self, data):
        self.private_load_static_data(data)


class PrivateFieldsAdminMixin(object):
    def get_add_hidden_fields(self, request):
        return {}

    def _mpsuhidden_map(self, request):
        if not hasattr(request, MPSU_HIDDEN):
            d = {}
            setattr(request, MPSU_HIDDEN, d)
        else:
            d = getattr(request, MPSU_HIDDEN)
        return d

    def _get_add_hidden_fields(self, request):
        d = self._mpsuhidden_map(request)
        v = d.get('fields')
        if v is None:
            v = d['fields'] = self.get_add_hidden_fields(request)
        return v

    def get_fieldsets(self, request, obj=None):
        fs = super(PrivateFieldsAdminMixin, self).get_fieldsets(request, obj)

        if hasattr(request, MPSU_HIDDEN):
            d = self._mpsuhidden_map(request)
            fields = d['fields'].keys()
            fs = fs + (
                (None,
                 {'fields': map(lambda _: _ + '_' + MPSU_HIDDEN, fields)}),)
        return fs

    def get_form(self, request, obj=None):
        form = super(PrivateFieldsAdminMixin, self).get_form(request, obj)

        if not obj:
            rl = self._get_add_hidden_fields(request)
            form._meta.mpsu_hidden_fields = rl
        return form

    def get_readonly_fields(self, request, obj=None, super_=False):
        rl = super(PrivateFieldsAdminMixin, self).get_readonly_fields(request,
                                                                      obj,
                                                                      super_)

        if not obj:
            fs = self._get_add_hidden_fields(request)
            if fs:
                for value in fs.itervalues():
                    if isinstance(value, dict) and 'set_readonly' in value:
                        for name in value['set_readonly']:
                            rl.append(name)

        return rl
