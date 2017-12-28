# coding=utf-8
from threading import local

from django.conf import settings
from modeldict import ModelDict
from modeldict.base import NoValue

from experiments.models import Experiment


thread_locals = local()


class LazyAutoCreate(object):
    """
    A lazy version of the setting is used so that tests can
    change the setting and still work
    """
    def __nonzero__(self):
        return self.__bool__()

    def __bool__(self):
        return getattr(settings, 'EXPERIMENTS_AUTO_CREATE', True)


class ExperimentManager(ModelDict):

    def _should_auto_create(self):
        try:
            return thread_locals.django_experiments_manager_auto_create
        except AttributeError:
            return self.auto_create

    def _set_auto_crate_override(self, value):
        if value is None:
            try:
                del thread_locals.django_experiments_manager_auto_create
            except AttributeError:
                pass
        else:
            thread_locals.django_experiments_manager_auto_create = value

    def get_experiment(self, experiment_name, auto_create=None):
        """
        Helper that mimics self[...] while allowing to override
        auto_create value.
        """
        self._set_auto_crate_override(auto_create)
        try:
            return self[experiment_name]
        except KeyError:
            return None

    def get_default(self, key):
        if not self._should_auto_create():
            return NoValue
        result = self.model.objects.get_or_create(**{self.key: key})[0]
        if self.instances:
            return result
        return getattr(result, self.value)


experiment_manager = ExperimentManager(
    Experiment,
    key='name',
    value='value',
    instances=True,
    auto_create=LazyAutoCreate(),
)
