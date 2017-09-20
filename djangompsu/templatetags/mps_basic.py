from importlib import import_module

from django import template
from django.utils.module_loading import import_string
from django.utils.safestring import mark_safe
from markdownx.settings import MARKDOWNX_MARKDOWNIFY_FUNCTION

register = template.Library()


@register.filter
def isa(value, *types_str):
    assert types_str
    types = []
    for tstr in types_str:
        split = tstr.split('.')
        if len(split) == 1:
            tp = eval(tstr)
        else:
            tp = getattr(import_module('.'.join(split[:-1])), split[-1])
        types.append(tp)

    return isinstance(value, types)


@register.tag
def to_list(value):
    return list(value)


class ToIntVarNode(template.Node):
    def __init__(self, var_names):
        self.var_names = var_names

    def render(self, context):
        for var_name in self.var_names:
            value = context[var_name]
            value = int(str(value))
            context[var_name] = value
        return u""


@register.tag
def to_int(parser, token):
    parts = token.split_contents()
    if len(parts) < 2:
        raise template.TemplateSyntaxError(
            "'increment' tag must be of the form:  {% increment <var_name> %}")
    return ToIntVarNode(parts[1:])


class IncrementVarNode(template.Node):
    def __init__(self, var_name, new_name=None):
        self.var_name = var_name
        self.new_name = new_name

    def render(self, context):
        value = context[self.var_name]
        var_name = self.new_name or self.var_name
        context[var_name] = value + 1
        return u""


@register.tag
def increment(parser, token):
    parts = token.split_contents()
    if len(parts) < 2:
        raise template.TemplateSyntaxError(
            "'increment' tag must be of the form:  {% increment <var_name> %}")
    return IncrementVarNode(*parts[1:])


@register.filter(name='get')
def get(value, key):
    try:
        return value[key]
    except KeyError:
        return None


@register.filter(name='markdown')
def markdown(value):
    if value is None: return ''

    value = value.strip()

    if not value:
        return ''

    markdownify = import_string(MARKDOWNX_MARKDOWNIFY_FUNCTION)
    return mark_safe(markdownify(value))
