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
        self.report = {'auto_enroll': {}}
        self.experiment_names = Experiment.objects.filter(
            auto_enroll=True).values_list('name', flat=True)
        self._conditionally_enroll()
        self.get_participant().save_report(self.report)

    def get_participant(self):
        """
        Returns an instance of experiments.utile.WebUser or its subclass
        Cached on the request.
        """
        return participant(self.request)

    def _conditionally_enroll(self):
        """
        Enroll current user in all experiments that are marked with
        `auto_enroll` and evaluate at least one of the conditionals
        positively.
        """
        for name in self.experiment_names:
            experiment = experiment_manager.get_experiment(
                name, auto_create=False)
            active = experiment.should_auto_enroll(self.request)
            if active:
                variate = self.get_participant().enroll(
                    experiment.name, experiment.alternative_keys)
            else:
                # notice: user can be enrolled in another alternative
                # (e.g. if previously visited another page), but as far as
                # "conditional experiments" are concerned, we have to enforce
                # the default here
                variate = experiment.default_alternative
            self._report(experiment, active, variate)

    def get_conditionally_enrolled_alternative(self, experiment_name):
        """
        Get enrolled alternative only if conditionals allow,
        control/default otherwise
        """
        experiment = experiment_manager.get_experiment(
            experiment_name, auto_create=False)
        if not experiment:
            return None
        participant = self.get_participant()
        if not experiment_name in self.report['auto_enroll']:
            # template tag called for a "regular" experiment
            # (i.e. auto_enroll = False) so we defer to regular
            # experiment model:
            return participant.get_alternative(experiment_name)
        experiment_report = self.report['auto_enroll'][experiment_name]
        return experiment_report.get('enrolled_alternative')

    def _report(self, instance, active, variate):
        """
        Populate self.report dict, used to set cookie with
        experiments data. The cookie is useful for debugging
        and verifying whether an experiment is running.
        """
        self.report['auto_enroll'][instance.name] = {
            'auto-enrolling': active,
            'enrolled_alternative': variate,
        }
