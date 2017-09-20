# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from djangompsu.base.admin import OwnedModelAdmin
from .models import *


class PolicyRuleInlineAdmin(admin.TabularInline):
    pass


def admin_policy_rule_factory(model):
    r = type(str(
        ('PolicyRuleOf%sInlineAdmin' %
         model.__name__.replace('PolicyRuleOf', ''))),
        (PolicyRuleInlineAdmin,), dict(
            model=model,
        ))
    return r


class PolicyAdmin(OwnedModelAdmin):
    default_fieldsets = (
        (None, {'fields': ('name', 'description')}),
        ('Users', {
            'fields': ('users',)
        }),
        ('Groups', {
            'fields': ('groups',)
        }),
        (_('Long Description'), {
            'classes': ('collapse',),
            'fields': ('long_description',)
        }),
    )

    list_display = ['__str__', 'description']
    search_fields = ['name']
    filter_horizontal = ['users', 'groups']


admin.site.register(Policy, PolicyAdmin)
