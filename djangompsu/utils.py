from __future__ import unicode_literals
import urllib
from django.utils.encoding import force_text

from django.core.urlresolvers import reverse

ADMIN_URLS = {}



def admin_url(view_name, model, *args, **kwargs):
    url_name = 'admin:%s_%s_%s' % (
    model._meta.app_label, model._meta.model_name, view_name)

    return reverse(url_name, args=args, kwargs=kwargs)


def join_and(collection, a=u' e ', f=u'%s', s=u', '):
    if not isinstance(collection, (tuple, list)):
        collection = list(collection)
    if not collection:
        return u''

    if len(collection) == 1:
        return f % collection[0]

    return a.join([s.join(map(lambda _: f % _, collection[:-1]))] + [
        f % collection[-1:][0]])


def admin_url_link_by_obj(view_name, model_obj, lb=None):
    lb = force_text(model_obj) if lb is None else getattr(model_obj, lb)
    return '<a href="%s">%s</a>' % (
        admin_url(view_name, model_obj.__class__, model_obj.pk), lb)


def admin_change_url(model_obj):
    return admin_url('change', model_obj.__class__, model_obj.pk)


def admin_change_url_link(model_obj, lb=None, label=None):
    if label is None:
        label = force_text(model_obj) if lb is None else getattr(model_obj, lb)
    return '<a href="%s">%s</a>' % (admin_change_url(model_obj), label)


def get_changelist_filters(request):
    if not hasattr(request, 'django_mpsu_changelist_filters'):
        v = request.GET.get('_changelist_filters')
        v = dict([_.split('=', 2) for _ in v.split('&')]) if v else {}
        request.django_mpsu_changelist_filters = v
        return v
    return request.django_mpsu_changelist_filters