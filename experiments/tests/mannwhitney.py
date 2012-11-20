from django.utils.unittest import TestCase

from scipy.stats import mannwhitneyu as scipy_mann_whitney
from experiments.significance import mann_whitney

class MannWhitneyTestCase(TestCase):
    def frequencies_to_list(self, frequencies):
        entries = []
        for entry,count in frequencies.items():
            entries.extend([entry] * count)
        return entries

    def test_empty_sets(self):
        mann_whitney(dict(), dict())

    def test_identical_ranges(self):
        distribution = dict((x,1) for x in range(50))
        self.assertMatchesSciPy(distribution, distribution)

    def test_many_repeated_values(self):
        self.assertMatchesSciPy({0: 100, 1: 50}, {0: 110, 1: 60})

    def test_large_range(self):
        distribution_a = dict((x,1) for x in range(10000))
        distribution_b = dict((x+1,1) for x in range(10000))
        self.assertMatchesSciPy(distribution_a, distribution_b)

    def test_very_different_sizes(self):
        distribution_a = dict((x,1) for x in range(10000))
        distribution_b = dict((x,1) for x in range(20))
        self.assertMatchesSciPy(distribution_a, distribution_b)

    def assertMatchesSciPy(self, distribution_a, distribution_b):
        our_u, our_p = mann_whitney(distribution_a, distribution_b)
        correct_u, correct_p = scipy_mann_whitney(
            self.frequencies_to_list(distribution_a),
            self.frequencies_to_list(distribution_b))
        self.assertEqual(our_u, correct_u, "U score incorrect")
        self.assertAlmostEqual(our_p, correct_p, msg="p value incorrect")
