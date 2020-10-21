from __future__ import absolute_import

from unittest import TestCase

from experiments.models import Experiment, Counters
from mock import patch


class ExperimentModelTestCase(TestCase):
    @patch.object(Counters, 'reset_prefix')
    def test_delete_resets_counters(self, reset_prefix_mock):
        experiment = Experiment.objects.create(name='test_experiment')
        experiment.delete()
        reset_prefix_mock.assert_called_with('test_experiment')
    
    @patch.object(Counters, 'reset_prefix')
    def test_delete_does_not_reset_counters_if_flag_not_set(self, reset_prefix_mock):
        experiment = Experiment.objects.create(name='test_experiment')
        experiment.delete(reset_counters=False)
        reset_prefix_mock.assert_not_called()
