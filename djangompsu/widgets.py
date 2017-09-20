from __future__ import unicode_literals

import re
from django import forms
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.forms.widgets import TextInput
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe


class UserFieldWidget(forms.Widget):
    def render(self, name, value, attrs=None):
        url = ''
        if value:
            value = User.objects.get(pk=value)
            url = reverse('admin:%s_%s_change' %(value._meta.app_label,  value._meta.model_name),  args=[value.pk])
        return mark_safe(render_to_string('mda/widgets/user_field.html',
                                          {'value': value, 'url': url}))


class FullNameWidget(TextInput):
    RE = re.compile(r'\s+', re.DOTALL)

    def value_from_datadict(self, data, files, name):
        value = super(FullNameWidget, self).value_from_datadict(data, files, name)
        if value:
            value = value.strip()
            value = self.RE.sub(' ', value)
        return value