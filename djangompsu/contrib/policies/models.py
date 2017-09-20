# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ...contrib.policies.mixins import PolicyMixin, model_policy_mixin_factory as _model_policy_factory
from ...modelmixins import mixin
from ...policies import Policy as PolicyClass


@mixin()
class Policy(PolicyMixin):
    pass


def model_policy_factory(model, policy_model=Policy):
    return _model_policy_factory(model, policy_model)


PolicyClass.model = Policy
