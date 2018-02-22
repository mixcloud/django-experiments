# coding=utf-8
from experiments.manager import experiment_manager
from experiments.utils import participant


class Experiments(object):
    """
    Helper for conditional experiments, meant to be added to request object
    """

    def __init__(self, context):
        from experiments.models import Experiment
        self.request = context['request']
        self.request.experiments = self
        self.context = context
        self.disabled_experiments = []
        self.report = {'conditional': {}}
        self.experiment_names = Experiment.objects.all().values_list(
            'name', flat=True)
        self._evaluate_conditionals()
        self.get_participant().set_disabled_experiments(
            self.disabled_experiments)

    def get_participant(self):
        """
        Returns an instance of experiments.utils.WebUser or its subclass
        Cached on the request.
        """
        return participant(self.request)

    def _evaluate_conditionals(self):
        """
        Populate request.experiments.disabled_experiments list with names
        of disabled experiments on the current request.
        """
        for name in self.experiment_names:
            experiment = experiment_manager.get_experiment(
                name, auto_create=False)
            if experiment:
                disabled = not experiment.is_enabled_by_conditionals(
                    self.request)
                alternative = None
                if disabled:
                    self.disabled_experiments.append(experiment.name)
                    alternative = experiment.default_alternative
                self._report(experiment, not disabled, alternative)

    def _report(self, instance, active, variate):
        """
        Populate self.report dict, used to set a JS variable with
        experiments data, only for staff users. This can be useful
        for debugging and verifying whether an experiment is running.
        """
        self.report['conditional'][instance.name] = {
            'disabled': not active,
            'enrolled_alternative': variate,
        }
