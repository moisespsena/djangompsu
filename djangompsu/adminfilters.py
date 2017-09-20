from django.contrib.admin import RelatedFieldListFilter
from django.db.models import BLANK_CHOICE_DASH
from django.utils.encoding import smart_text


class PolicyRelatedFieldListFilter(RelatedFieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        super(PolicyRelatedFieldListFilter, self).__init__(field, request, params, model, model_admin, field_path)

    def get_choices(self, request, include_blank=True, blank_choice=BLANK_CHOICE_DASH, limit_choices_to=None):
        """Returns choices with a default blank choices included, for use
        as SelectField choices for this field."""
        blank_defined = False
        choices = list(self.choices) if self.choices else []
        named_groups = choices and isinstance(choices[0][1], (list, tuple))
        if not named_groups:
            for choice, __ in choices:
                if choice in ('', None):
                    blank_defined = True
                    break

        first_choice = (blank_choice if include_blank and
                                        not blank_defined else [])
        if self.choices:
            return first_choice + choices
        rel_model = self.rel.to
        limit_choices_to = limit_choices_to or self.get_limit_choices_to()
        if hasattr(self.rel, 'get_related_field'):
            lst = [(getattr(x, self.rel.get_related_field().attname),
                    smart_text(x))
                   for x in rel_model.filter_objects_by_request(request, rel_model._default_manager.complex_filter(
                    limit_choices_to))]
        else:
            lst = [(x._get_pk_val(), smart_text(x))
                   for x in rel_model._default_manager.complex_filter(
                    limit_choices_to)]
        return first_choice + lst

    def _field_choices(self, field, request, include_blank=True, blank_choice=BLANK_CHOICE_DASH,
                    limit_to_currently_related=False):
        """
        Returns choices with a default blank choices included, for use as
        SelectField choices for this field.

        Analog of django.db.models.fields.Field.get_choices(), provided
        initially for utilization by RelatedFieldListFilter.
        """
        first_choice = blank_choice if include_blank else []
        queryset = field.related_model.filter_objects_by_request(request, field.related_model._default_manager.all())
        if limit_to_currently_related:
            queryset = queryset.complex_filter(
                {'%s__isnull' % field.related_model._meta.model_name: False}
            )
        lst = [(x._get_pk_val(), smart_text(x)) for x in queryset]
        return first_choice + lst

    def field_choices(self, field, request, model_admin):
        return self._field_choices(field, request, include_blank=False)

    def create(cls, field, request, params, model, model_admin, field_path):
        return super(PolicyRelatedFieldListFilter, cls).create(field, request, params, model, model_admin, field_path)
