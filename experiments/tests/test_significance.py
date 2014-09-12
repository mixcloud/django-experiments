from django.utils.unittest import TestCase

from experiments.significance import mann_whitney, chi_square_p_value


# The hardcoded p and u values in these tests were calculated using scipy
class MannWhitneyTestCase(TestCase):
    longMessage = True

    def test_empty_sets(self):
        mann_whitney(dict(), dict())

    def test_identical_ranges(self):
        distribution = dict((x, 1) for x in range(50))
        self.assertUandPCorrect(distribution, distribution, 1250.0, 0.49862467827855483)

    def test_many_repeated_values(self):
        self.assertUandPCorrect({0: 100, 1: 50}, {0: 110, 1: 60}, 12500.0, 0.35672951675909859)

    def test_large_range(self):
        distribution_a = dict((x, 1) for x in range(10000))
        distribution_b = dict((x + 1, 1) for x in range(10000))
        self.assertUandPCorrect(distribution_a, distribution_b, 49990000.5, 0.49023014794874586)

    def test_very_different_sizes(self):
        distribution_a = dict((x, 1) for x in range(10000))
        distribution_b = dict((x, 1) for x in range(20))
        self.assertUandPCorrect(distribution_a, distribution_b, 200.0, 0)

    def assertUandPCorrect(self, distribution_a, distribution_b, u, p):
        our_u, our_p = mann_whitney(distribution_a, distribution_b)
        self.assertEqual(our_u, u, "U score incorrect")
        self.assertAlmostEqual(our_p, p, msg="p value incorrect")

