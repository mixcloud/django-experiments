from django.utils.unittest import TestCase

from experiments import stats

class StatsTestCase(TestCase):
    def test_flatten(self):
        self.assertEqual(
            list(stats.flatten([1,[2,[3]],4,5])),
            [1,2,3,4,5]
            )
