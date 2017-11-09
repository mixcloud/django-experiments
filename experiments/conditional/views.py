# coding=utf-8
from __future__ import absolute_import


import logging


logger = logging.getLogger(__name__)


class Experiments(object):
    """
    Handles everything related to evaluating conditional experiments.
    Initialised by ExperimentsMixin().
    Separate from the mixin to avoid polluting the view class namespace.
    """

    def __init__(self, context):
        from ..models import Experiment
        self.request = context['request']
        self.context = context
        self.report = {
            'auto_enroll': {},
        }
        self.instances = Experiment.objects.filter(auto_enroll=True)

    def get_participant(self):
        """
        Returns an instance of experiments.utile.WebUser or its subclass
        Cached on the request.
        """
        from ..utils import participant
        return participant(self.request)

    def conditionally_enroll(self):
        """
        Enroll current user in all experiments that are marked with
        `auto_enroll` and evaluate at least one of the conditionals
        positively.
        """
        for i in self.instances:
            active = i.should_auto_enroll(self.request)
            if active:
                variate = self.get_participant().enroll(
                    i.name, i.alternative_keys)
            else:
                variate = self.get_participant().get_alternative(i.name)
            self._report(i, active, variate)

    def _report(self, instance, active, variate):
        """
        Populate self.report dict, used to set cookie with
        experiments data. The cookie is useful for debugging
        and verifying whether an experiment is running.
        """
        self.report['auto_enroll'][instance.name] = {
            'auto-enrolling': active,
            'enrolled_variate': variate,
        }


class ExperimentsMixin(object):
    """Mixin for View classes (class based views)"""

    def dispatch(self, request, *args, **kwargs):
        """Instantiates the Experiments object for the current request"""
        response = super(ExperimentsMixin, self).dispatch(
            request, *args, **kwargs)
        return response
