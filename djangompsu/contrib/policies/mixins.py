# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User, Group
from django.db import models
from django.utils.translation import ugettext_lazy as _

from ...base.models import Owned
from ...modelmixins import F, ModelMixin, mixin
from ...models import MarkdownField
from ...policies import *


class PolicyMixin(Owned):
    name = F(models.CharField, max_length=100, unique=True)
    description = F(models.CharField, max_length=255, blank=True, default='')
    long_description = F(MarkdownField, blank=True, default='')
    users = F(models.ManyToManyField, User, db_index=True, blank=True,
              related_name='policies')
    groups = F(models.ManyToManyField, Group, db_index=True, blank=True,
               related_name='policies')

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']
        unique_together = ('name',)


def set_policy_class(factory, mixinClass, ak):
    ak[0] += (mixinClass.PolicyMeta.policy_model,)


class PolicyRuleMixin(ModelMixin):
    policy_model = None
    policy = F(models.ForeignKey, db_index=True, on_delete=models.CASCADE, fcb=[set_policy_class])
    target = F(models.ForeignKey, db_index=True, on_delete=models.CASCADE, related_name='policyrules')
    perms = F(models.IntegerField, default=NONE, choices=CHOICES)

    def __unicode__(self):
        return unicode(self.target)

    __str__ = __unicode__


def model_policy_mixin_factory(model, policy_model_):
    class Meta:
        unique_together = ('policy', 'target')
        verbose_name = _('Rule of %s') % model._meta.verbose_name
        verbose_name_plural = _('Rules of %s') % model._meta.verbose_name_plural

    class PolicyMeta:
        policy_model = policy_model_

    model.PolicyMeta = PolicyMeta

    r = type(str('PolicyRuleOf%s' % model.__name__), (PolicyRuleMixin,), {
        'Meta': Meta,
        '__module__': model.__module__,
        'policy': PolicyRuleMixin.policy(
            related_name='rules_%s' % model.__name__.lower()),
        'target': PolicyRuleMixin.target(model),
        'PolicyMeta': PolicyMeta
    })

    return r


def model_policy_factory(model, policy_model):
    return mixin()(model_policy_mixin_factory(model, policy_model))
