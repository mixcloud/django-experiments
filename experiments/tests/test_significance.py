from unittest import TestCase
import random

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

class ChiSquare(TestCase):
    def test_equal(self):
        self.assertChiSquareCorrect(((100, 10), (200, 20)), 0, 1)
        self.assertChiSquareCorrect(((100, 100, 100), (200, 200, 200), (300, 300, 300)), 0, 1)

    def test_error(self):
        self.assertRaises(TypeError, chi_square_p_value((1,)))
        self.assertRaises(TypeError, chi_square_p_value(((1,2,3))))

    def test_is_none(self):
        self.assertEqual(chi_square_p_value(((1, 1), (1, -1))), (None, None), "Negative numbers should not be allowed")
        self.assertEqual(chi_square_p_value(((0, 0), (0, 0))), (None, None), "Zero sample size should not be allowed")
        self.assertIsNone(chi_square_p_value(((1,), (1, 2))), "Unequal matrices should not be allowed")
        self.assertIsNone(chi_square_p_value(((1, 2, 3), (1, 2, 3), (1, 2))), "Unequal matrices should not be allowed")
        self.assertIsNone(chi_square_p_value(((100, 10), (200, 20), (300, 30), (400, 40))), "Matrices have to be square")

    def test_stress(self):
        # Generate a large matrix
        matrix = []
        for col in range(0, 100):
            matrix.append([])
            for row in range(0, 100):
                matrix[col].append(random.randint(0, 10))

        self.assertIsNotNone(chi_square_p_value(matrix))

    def test_accept_hypothesis(self):
        self.assertChiSquareCorrect(((36, 14), (30, 25)), 3.418, 0.065, 3)
        self.assertChiSquareCorrect(((100, 50), (210, 110)), 0.04935, 0.8242, 3)
        self.assertChiSquareCorrect(((100, 50, 10), (110, 50, 10), (140, 55, 11)), 1.2238, 0.8741, 3)

    def test_reject_hypothesis(self):
        self.assertChiSquareCorrect(((100, 20), (200, 20)), 4.2929, 0.0383, 4)
        self.assertChiSquareCorrect(((100, 50, 10), (110, 70, 20), (140, 55, 6)), 13.0217, 0.0111, 3)

    def assertChiSquareCorrect(self, matrix, observed_test_statistic, p_value, accuracy=7):
        observed_test_statistic_result, p_value_result = chi_square_p_value(matrix)
        self.assertAlmostEqual(observed_test_statistic_result, observed_test_statistic, accuracy, 'Wrong observed result')
        self.assertAlmostEqual(p_value_result, p_value, accuracy, 'Wrong P Value')

