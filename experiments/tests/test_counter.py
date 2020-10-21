from __future__ import absolute_import

from unittest import TestCase

from experiments import counters
from experiments.experiment_counters import ExperimentCounter
from experiments.models import Experiment
from mock import patch

TEST_KEY = 'CounterTestCase'


class CounterTestCase(TestCase):
    def setUp(self):
        self.counters = counters.Counters()
        self.counters.reset(TEST_KEY)
        self.assertEqual(self.counters.get(TEST_KEY), 0)

    def tearDown(self):
        self.counters.reset(TEST_KEY)

    def test_add_item(self):
        self.counters.increment(TEST_KEY, 'fred')
        self.assertEqual(self.counters.get(TEST_KEY), 1)

    def test_add_multiple_items(self):
        self.counters.increment(TEST_KEY, 'fred')
        self.counters.increment(TEST_KEY, 'barney')
        self.counters.increment(TEST_KEY, 'george')
        self.counters.increment(TEST_KEY, 'george')
        self.assertEqual(self.counters.get(TEST_KEY), 3)

    def test_add_duplicate_item(self):
        self.counters.increment(TEST_KEY, 'fred')
        self.counters.increment(TEST_KEY, 'fred')
        self.counters.increment(TEST_KEY, 'fred')
        self.assertEqual(self.counters.get(TEST_KEY), 1)

    def test_get_frequencies(self):
        self.counters.increment(TEST_KEY, 'fred')
        self.counters.increment(TEST_KEY, 'barney')
        self.counters.increment(TEST_KEY, 'george')
        self.counters.increment(TEST_KEY, 'roger')
        self.counters.increment(TEST_KEY, 'roger')
        self.counters.increment(TEST_KEY, 'roger')
        self.counters.increment(TEST_KEY, 'roger')
        self.assertEqual(self.counters.get_frequencies(TEST_KEY), {1: 3, 4: 1})

    def test_delete_key(self):
        self.counters.increment(TEST_KEY, 'fred')
        self.counters.reset(TEST_KEY)
        self.assertEqual(self.counters.get(TEST_KEY), 0)

    def test_clear_value(self):
        self.counters.increment(TEST_KEY, 'fred')
        self.counters.increment(TEST_KEY, 'fred')
        self.counters.increment(TEST_KEY, 'fred')
        self.counters.increment(TEST_KEY, 'barney')
        self.counters.increment(TEST_KEY, 'barney')
        self.counters.clear(TEST_KEY, 'fred')

        self.assertEqual(self.counters.get(TEST_KEY), 1)
        self.assertEqual(self.counters.get_frequencies(TEST_KEY), {2: 1})
    
    def test_reset_all(self):
        experiment = Experiment.objects.create(name='reset_test')
        other_experiment = Experiment.objects.create(name='reset_test_other')
        experiment_counter = ExperimentCounter()

        for exp in [experiment, other_experiment]:
            experiment_counter.increment_participant_count(exp, 'alt', 'fred')
            experiment_counter.increment_participant_count(exp, 'alt', 'fred')
            experiment_counter.increment_participant_count(exp, 'alt', 'fred')
            experiment_counter.increment_goal_count(exp, 'alt', 'goal1', 'fred')
            experiment_counter.increment_goal_count(exp, 'alt', 'goal2', 'fred')
            experiment_counter.increment_participant_count(exp, 'control', 'barney')
            experiment_counter.increment_participant_count(exp, 'control', 'wilma')
            experiment_counter.increment_participant_count(exp, 'control', 'betty')
            experiment_counter.increment_goal_count(exp, 'control', 'goal1', 'betty')
        
        self.counters.reset_prefix(experiment.name)
        self.assertEqual(experiment_counter.participant_count(experiment, 'alt'), 0)
        self.assertEqual(experiment_counter.participant_count(experiment, 'control'), 0)
        self.assertEqual(experiment_counter.goal_count(experiment, 'control', 'goal1'), 0)

        self.assertEqual(experiment_counter.participant_count(other_experiment, 'alt'), 1)
        self.assertEqual(experiment_counter.participant_count(other_experiment, 'control'), 3)
        self.assertEqual(experiment_counter.goal_count(other_experiment, 'control', 'goal1'), 1)
        

    @patch('experiments.counters.Counters._redis')
    def test_should_return_tuple_if_failing(self, patched__redis):
        patched__redis.side_effect = Exception

        self.assertEqual(self.counters.get_frequencies(TEST_KEY), dict())
