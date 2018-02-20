from django.conf import settings

from modeldict import ModelDict

from experiments.models import Experiment


class LazyAutoCreate(object):
    """
    A lazy version of the setting is used so that tests can change the setting
    and still work
    """
    def __nonzero__(self):
        return self.__bool__()

    def __bool__(self):
        return getattr(settings, 'EXPERIMENTS_AUTO_CREATE', True)


class ExperimentManager(ModelDict):
    def get_experiment(self, experiment_name):
        # Helper that uses self[...] so that the experiment is auto created
        # where desired
        try:
            return self[experiment_name]
        except KeyError:
            return None


experiment_manager = ExperimentManager(
    Experiment, key='name', value='value', instances=True,
    auto_create=LazyAutoCreate())
