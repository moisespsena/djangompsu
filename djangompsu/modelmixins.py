"""
Mixin support for django models
"""
import copy
import sys

from django.db import models


class Counter(object):
    def __init__(self):
        self.value = -1

    def increment(self):
        self.value += 1
        return self.value


class Factory(object):
    COUNTER = Counter()

    def __init__(self, cls, *args, **kwargs):
        counter = kwargs.pop('__counter', None)
        if counter is None:
            counter = self.COUNTER.increment()
        self.counter = counter
        self.cls = cls
        self.args = args
        self.kwargs = kwargs
        if 'kw_' in kwargs:
            raise Exception('kw_ keyarg deprecated.')

        self.callbacks = kwargs.pop('fcb', [])
        self.data = kwargs.pop('fdata', {})

    def create(self, mixinClass):
        if self.callbacks:
            ak = [self.args, self.kwargs]
            for v in self.callbacks:
                v(self, mixinClass, ak)
            cls = self.cls(*ak[0], **ak[1])
        else:
            cls = self.cls(*self.args, **self.kwargs)

        cls.factory = self
        return cls

    def __getitem__(self, item):
        return self.data[item]

    def __delitem__(self, key):
        del self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __call__(self, *args, **kwargs):
        new = self.__class__(self.cls, __counter=self.counter)
        new.args = self.args + args
        new.callbacks = self.callbacks + kwargs.pop('fcb', [])
        new.data = copy.copy(self.data)
        new.data.update(kwargs.pop('fdata', {}))
        new.kwargs = copy.copy(self.kwargs)
        new.kwargs.update(kwargs)
        return new


F = Factory


def mixin_attrs(cls):
    if cls == ModelMixin: return []
    attrs = {}

    for base in cls.__bases__:
        attrs.update(mixin_attrs(base))

    for k, v in cls.__dict__.items():
        if not isinstance(v, Factory):
            v = copy.copy(v)
        attrs[k] = v

    return attrs


def copy_field(f):
    fp = copy.copy(f)
    fp.creation_counter = models.Field.creation_counter
    models.Field.creation_counter += 1

    if hasattr(f, "model"):
        del fp.attname
        del fp.column
        del fp.model

    return fp


class SuperMethod(object):
    def __init__(self, cls, self_, default=None):
        self.__s = super(cls, self_)
        self.__default = None

    def __getattr__(self, item):
        if hasattr(self.__s, item):
            return getattr(self.__s, item)
        return lambda *args, **kwargs: self.__default


class ModelMixin(object):
    pass


def field_title(mixin, field_name):
    attr = getattr(mixin.MixinClass, field_name)
    return attr.kwargs.get('verbose_name', field_name)


class MixinProperty(object):
    def __init__(self, cls):
        self.cls = cls

    def __get__(self, instance, owner):
        return self.cls


def mixin(base_model=models.Model):
    def make(cls):
        assert issubclass(cls, ModelMixin), "class isn't subclass of ModelMixin"
        attrs = dict(cls.__dict__)
        factories = []

        for k, v in mixin_attrs(cls).iteritems():
            if isinstance(v, Factory):
                factories.append((k, v))

        attrs.update(dict(map(lambda _: (_[0], _[1].create(cls)), sorted(factories, key=lambda _: _[1].counter))))
        name = cls.__name__
        cls.__name__ = '_' + cls.__name__ + "Mixin"
        setattr(sys.modules[cls.__module__], cls.__name__, cls)

        bases = cls.__bases__ + (base_model,)
        attrs['MixinClass'] = attrs['Mixin'] = MixinProperty(cls)
        new_cls = type(name, bases, attrs)
        return new_cls

    return make


def class_vname(cls):
    return cls.MixinClass.Meta.verbose_name
