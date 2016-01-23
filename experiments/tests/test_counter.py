from __future__ import absolute_import

from unittest import TestCase

from experiments import counters

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
