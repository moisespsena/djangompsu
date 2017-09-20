# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms

from .widgets import UserFieldWidget, FullNameWidget

__author__ = 'moi'

class FullNameField(forms.CharField):
    widget = FullNameWidget


class UserField(forms.TextInput):
    def __init__(self, *args, **kwargs):
        self.widget = UserFieldWidget()
        super(UserField, self).__init__(*args, **kwargs)