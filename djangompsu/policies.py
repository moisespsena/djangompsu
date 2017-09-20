# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import connection
from django.db.models import BLANK_CHOICE_DASH
from django.utils.translation import ugettext_lazy as _

NONE = 0
SHOW_INFO = 1
SHOW = SHOW_INFO | 2
CHANGE_INLINES = SHOW | 4
CHANGE = SHOW | CHANGE_INLINES | 8
DELETE = CHANGE | 16
ALL = DELETE

CHOICES = (
    (NONE, _('Nothing')),
    (SHOW_INFO, _('Show Info')),
    (SHOW, _('Show')),
    (CHANGE, _('Change')),
    (DELETE, _('Delete')),
    (ALL, _('All')),
)


def filter_model_by_policy(model, user, perms=None):
    rule_tbname = '%sruleof%s' % (model.PolicyMeta.policy_model._meta.db_table, model.__name__.lower())
    if perms is None:
        perms = getattr(model, 'POLICY_DEFAULT_PERM', SHOW_INFO)

    if perms is None:
        return 'TRUE'

    sql = """
        "{1}"."owner_id" = {0}
        OR
        EXISTS (
            SELECT 1
            FROM "{2}"
            INNER JOIN "{3}" 
                ON ( "{3}"."policy_id" = "{2}"."id" )
            WHERE 
                "{3}"."target_id" = "{1}"."id"
                AND ( ("{3}"."perms" & {4}) = {4} )
                AND (
                    EXISTS (
                        SELECT 1
                        FROM "{2}_groups"
                        INNER JOIN "auth_group" 
                            ON ( "{2}_groups"."group_id" = "auth_group"."id" )
                        INNER JOIN "auth_user_groups" 
                            ON ( "auth_group"."id" = "auth_user_groups"."group_id" )
                        WHERE
                            "auth_user_groups"."user_id" = {0}
                            AND
                            "{2}"."id" = "{2}_groups"."policy_id"
                    ) OR EXISTS (
                        SELECT 1
                        FROM "{2}_users"
                        WHERE
                            "{2}_users"."user_id" = {0}
                            AND
                            "{2}"."id" = "{2}_users"."policy_id"
                    )
                )
        )
        """.format(
        user.pk,
        model._meta.db_table,
        model.PolicyMeta.policy_model._meta.db_table,
        rule_tbname,
        perms)

    return sql


def filter_related_by_policy(base_model, model, user, perms=SHOW_INFO):
    base_model_fname, base_model = base_model
    rule_tbname = '%sruleof%s' % (base_model.PolicyMeta.policy_model._meta.db_table, base_model.__name__.lower())

    sql = """
    EXISTS (
        SELECT 1
        FROM "{1}"
        LEFT JOIN "{3}" 
            ON ( "{1}"."id" = "{3}"."target_id" ) 
        LEFT JOIN "{2}" 
            ON ( "{3}"."policy_id" = "{2}"."id" )
        WHERE 
            "{1}"."id" = "{5}"."{4}_id"
            AND (
                "{1}".owner_id = {0}
                OR (
                    ( ("{3}"."perms" & {6}) = {6} )
                    AND (
                        EXISTS (
                            SELECT 1
                            FROM "{2}_groups"
                            INNER JOIN "auth_group" 
                                ON ( "{2}_groups"."group_id" = "auth_group"."id" )
                            INNER JOIN "auth_user_groups" 
                                ON ( "auth_group"."id" = "auth_user_groups"."group_id" )
                            WHERE
                                "auth_user_groups"."user_id" = {0}
                                AND
                                "{2}"."id" = "{2}_groups"."policy_id"
                        ) OR EXISTS (
                            SELECT 1
                            FROM "{2}_users"
                            WHERE
                                "{2}_users"."user_id" = {0}
                                AND
                                "{2}"."id" = "{2}_users"."policy_id"
                        )
                    )
                )
            )
    )
    """.format(
        user.pk,
        base_model._meta.db_table,
        base_model.PolicyMeta.policy_model._meta.db_table,
        rule_tbname,
        base_model_fname,
        model._meta.db_table,
        perms,
    )

    print(sql)
    return sql


def get_policy_by_model(policy_class, model_instance, user):
    if model_instance.owner_id == user.pk:
        return policy_class().all()

    model = model_instance.__class__
    rule_tbname = '%sruleof%s' % (policy_class.model._meta.db_table, model.__name__.lower())

    sql = """
        SELECT perms
        FROM "{3}"
        INNER JOIN "{2}" 
            ON ( "{3}"."policy_id" = "{2}"."id" )
        WHERE 
            "{3}"."target_id" = {4}
            AND (
                EXISTS (
                    SELECT 1
                    FROM "{2}_groups"
                    INNER JOIN "auth_group" 
                        ON ( "{2}_groups"."group_id" = "auth_group"."id" )
                    INNER JOIN "auth_user_groups" 
                        ON ( "auth_group"."id" = "auth_user_groups"."group_id" )
                    WHERE
                        "auth_user_groups"."user_id" = {0}
                        AND
                        "{2}"."id" = "{2}_groups"."policy_id"
                ) OR EXISTS (
                    SELECT 1
                    FROM "{2}_users"
                    WHERE
                        "{2}_users"."user_id" = {0}
                        AND
                        "{2}"."id" = "{2}_users"."policy_id"
                )
            )
        """.format(user.pk,
                   model._meta.db_table,
                   policy_class.model._meta.db_table,
                   rule_tbname,
                   model_instance.pk)

    p = policy_class()

    with connection.cursor() as cursor:
        cursor.execute(sql)

        for row in cursor.fetchall():
            p.value |= row[0]

    return p

def qs_req_by_model(model, request, qs):
    if qs is None:
        qs = model.objects.all()
    if not request.user.is_superuser:
        qs = qs.extra(where=[filter_model_by_policy(model, request.user)])
    return qs


def qs_req_by_related(model, relateds, request, qs):
    if not request.user.is_superuser:
        wheres = [filter_related_by_policy(related, model, request.user) for related in relateds]
        qs = qs.extra(where=wheres)
    return qs


# TODO: Add support for owner group
# TODO: Add delete perm

class Policy(object):
    model = None

    def __init__(self, value=0):
        self.value = value

    def has(self, v):
        return self.value & v == v

    @property
    def change(self):
        return self.has(CHANGE)

    @property
    def change_inlines(self):
        return self.has(CHANGE_INLINES)

    @property
    def show(self):
        return self.has(SHOW)

    @property
    def show_info(self):
        return self.has(SHOW_INFO)

    @property
    def delete(self):
        return self.has(DELETE)

    def all(self):
        self.value = ALL
        return self

    def __unicode__(self):
        return u'Policy{show_info=%r, show=%r, change=%r}' % (self.show_info, self.show, self.change)

    @classmethod
    def by_model(cls, model, user):
        return get_policy_by_model(cls, model, user)

    @classmethod
    def by_related_model(cls, fnames, model, user):
        p = cls()
        for fname in fnames:
            related_model = getattr(model, fname)
            if not related_model is None:
                mp = related_model.policy(user)
                p.value |= mp.value
        return p
