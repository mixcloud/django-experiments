from __future__ import absolute_import

from django.utils.unittest import TestCase

from experiments import stats
from experiments import counters

class StatsTestCase(TestCase):
    def test_flatten(self):
        self.assertEqual(
            list(stats.flatten([1,[2,[3]],4,5])),
            [1,2,3,4,5]
            )

TEST_KEY = 'CounterTestCase'

class CounterTestCase(TestCase):
    def setUp(self):
        counters.counter_reset(TEST_KEY)
        self.assertEqual(counters.counter_get(TEST_KEY), 0)

    def tearDown(self):
        counters.counter_reset(TEST_KEY)

    def test_add_item(self):
        counters.counter_increment(TEST_KEY, 'fred')
        self.assertEqual(counters.counter_get(TEST_KEY), 1)

    def test_add_multiple_items(self):
        counters.counter_increment(TEST_KEY, 'fred')
        counters.counter_increment(TEST_KEY, 'barney')
        counters.counter_increment(TEST_KEY, 'george')
        self.assertEqual(counters.counter_get(TEST_KEY), 3)

    def test_add_duplicate_item(self):
        counters.counter_increment(TEST_KEY, 'fred')
        counters.counter_increment(TEST_KEY, 'fred')
        counters.counter_increment(TEST_KEY, 'fred')
        self.assertEqual(counters.counter_get(TEST_KEY), 1)

    def test_delete_key(self):
        counters.counter_increment(TEST_KEY, 'fred')
        counters.counter_reset(TEST_KEY)
        self.assertEqual(counters.counter_get(TEST_KEY), 0)
