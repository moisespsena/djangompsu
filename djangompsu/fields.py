# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from .forms import FullNameField as FullNameFormField
from .formfields import MarkdownFormField


class FullNameField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 50)
        super(FullNameField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {
            'form_class': FullNameFormField
        }
        defaults.update(kwargs)
        return super(FullNameField, self).formfield(**defaults)



DAYS_OF_WEEK_CHOICES = (
    (1, _('Sunday')),
    (2, _('Monday')),
    (3, _('Tuesday')),
    (4, _('Wednesday')),
    (5, _('Thursday')),
    (6, _('Friday')),
    (7, _('Saturday')),
)


class WeekdayField(models.IntegerField):
    def __init__(self, *args, **kwargs):
        kwargs['choices'] = DAYS_OF_WEEK_CHOICES
        super(WeekdayField, self).__init__(*args, **kwargs)

class UniqueBooleanField(models.BooleanField):
    def __init__(self, *args, **kwargs):
        self.unique_value = kwargs.pop('unique_value', True)
        self.unique_together = kwargs.pop('unique_together', ())
        super(UniqueBooleanField, self).__init__(*args, **kwargs)

    def pre_save(self, obj, add):
        model = obj.__class__
        objects = model.objects

        if self.unique_together:
            filters = {f: getattr(obj, f) for f in self.unique_together}
            objects = objects.filter(**filters)

        value = getattr(obj, self.attname)
        # If exists anothers objects with self.unique_value, set others as not self.unique_value
        if value is self.unique_value:
            objects.update(**{self.attname: not self.unique_value})
        return value

class MarkdownField(models.TextField):
    def formfield(self, **kwargs):
        defaults = {'form_class': MarkdownFormField}
        defaults.update(kwargs)
        return super(MarkdownField, self).formfield(**defaults)