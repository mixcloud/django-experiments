from django.test import TestCase

from experiments.templatetags.experiments import _parse_token_contents


class ExperimentTemplateTagTestCase(TestCase):
    """These test cases are rather nastily coupled, and are mainly intended to check the token parsing code"""

    def test_returns_with_standard_values(self):
        token_contents = ('experiment', 'backgroundcolor', 'blue')
        experiment_name, alternative, weight, user_resolvable = _parse_token_contents(token_contents)
        self.assertEqual(experiment_name, 'backgroundcolor')
        self.assertEqual(alternative, 'blue')

    def test_handles_old_style_weight(self):
        token_contents = ('experiment', 'backgroundcolor', 'blue', '10')
        experiment_name, alternative, weight, user_resolvable = _parse_token_contents(token_contents)
        self.assertEqual(weight, '10')

    def test_handles_labelled_weight(self):
        token_contents = ('experiment', 'backgroundcolor', 'blue', 'weight=10')
        experiment_name, alternative, weight, user_resolvable = _parse_token_contents(token_contents)
        self.assertEqual(weight, '10')

    def test_handles_user(self):
        token_contents = ('experiment', 'backgroundcolor', 'blue', 'user=commenter')
        experiment_name, alternative, weight, user_resolvable = _parse_token_contents(token_contents)
        self.assertEqual(user_resolvable.var, 'commenter')

    def test_handles_user_and_weight(self):
        token_contents = ('experiment', 'backgroundcolor', 'blue', 'user=commenter', 'weight=10')
        experiment_name, alternative, weight, user_resolvable = _parse_token_contents(token_contents)
        self.assertEqual(user_resolvable.var, 'commenter')
        self.assertEqual(weight, '10')

    def test_raises_on_insufficient_arguments(self):
        token_contents = ('experiment', 'backgroundcolor')
        self.assertRaises(ValueError, lambda: _parse_token_contents(token_contents))
