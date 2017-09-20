# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import models
from django.utils.translation import ugettext_lazy as _

from djangompsu.policies import Policy, qs_req_by_related
from ..modelmixins import ModelMixin, F
from ..models import MarkdownField
from ..policies import qs_req_by_model


class CreationInfo(ModelMixin):
    created = F(models.DateTimeField, auto_now_add=True,
                verbose_name='criado em')
    created_by = F(models.ForeignKey, User,
                   related_name='%(app_label)s_%(class)s_created_by',
                   verbose_name='criado por')


class OwnedCreationInfo(CreationInfo):
    owner = F(models.ForeignKey, User,
              related_name='%(app_label)s_%(class)s_owner',
              verbose_name='proprietário')


class Owned(CreationInfo):
    updated = F(models.DateTimeField, auto_now=True,
                verbose_name='atualizado em')
    updated_by = F(models.ForeignKey, User,
                   related_name='%(app_label)s_%(class)s_updated_by',
                   verbose_name='atualizado por')
    owner = F(models.ForeignKey, User,
              related_name='%(app_label)s_%(class)s_owner',
              verbose_name='proprietário')


class SimpleNamedWithDescription(ModelMixin):
    nome = F(models.CharField, max_length=100)
    descricao = F(models.CharField, max_length=255, blank=True, default='',
                  verbose_name='descrição')

    def __unicode__(self):
        return self.nome


class NamedWithDescription(SimpleNamedWithDescription):
    descricao_longa = F(MarkdownField, blank=True, default='',
                        verbose_name=_('descrição longa'))


class OwnedNamedDescription(Owned, NamedWithDescription):
    pass


class SimpleOwnedNamedDescription(Owned, SimpleNamedWithDescription):
    pass


class ModelWithPolicy(ModelMixin):
    policy_class = Policy
    policy_related = ()
    _policy = None

    def policy(self, user):
        if self._policy is None:
            self._policy = dict()

        if not user.pk in self._policy:
            if self.policy_related:
                self._policy[user.pk] = self.policy_class.by_related_model(self.policy_related, self, user)
            else:
                self._policy[user.pk] = self.policy_class.by_model(self, user)
        return self._policy[user.pk]

    def has_perm(self, user, perm):
        return self.policy(user).has(perm)

    def has_perm_or_error(self, user, perm):
        if not self.has_perm(user, perm):
            raise PermissionDenied

    @classmethod
    def _filter_objects_by_request(cls, request, qs=None):
        return qs_req_by_model(cls, request, qs)

    @classmethod
    def _filter_objects_by_request_related(cls, request, qs=None):
        relateds = [(att, getattr(cls, att).field.related_model) for att in cls.policy_related]
        return qs_req_by_related(cls, relateds, request, qs)

    @classmethod
    def filter_objects_by_request(cls, request, qs=None):
        if cls.policy_related:
            cls.filter_objects_by_request = cls._filter_objects_by_request_related
        else:
            cls.filter_objects_by_request = cls._filter_objects_by_request

        return cls.filter_objects_by_request(request, qs)
