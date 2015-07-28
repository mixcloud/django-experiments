from django.contrib.auth.models import User
from django.template import Template, Context
from django.test import TestCase, override_settings, RequestFactory
from experiments.models import Experiment

from experiments.templatetags.experiments import _parse_token_contents
from experiments.utils import participant


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


class ExperimentAutoCreateTestCase(TestCase):
    @override_settings(EXPERIMENTS_AUTO_CREATE=False)
    def test_template_auto_create_off(self):
        request = RequestFactory().get('/')
        request.user = User.objects.create(username='test')
        Template("{% load experiments %}{% experiment test_experiment control %}{% endexperiment %}").render(Context({'request': request}))
        self.assertFalse(Experiment.objects.filter(name="test_experiment").exists())

    def test_template_auto_create_on(self):
        request = RequestFactory().get('/')
        request.user = User.objects.create(username='test')
        Template("{% load experiments %}{% experiment test_experiment control %}{% endexperiment %}").render(Context({'request': request}))
        self.assertTrue(Experiment.objects.filter(name="test_experiment").exists())

    @override_settings(EXPERIMENTS_AUTO_CREATE=False)
    def test_view_auto_create_off(self):
        user = User.objects.create(username='test')
        participant(user=user).enroll('test_experiment_y', alternatives=['other'])
        self.assertFalse(Experiment.objects.filter(name="test_experiment_y").exists())

    def test_view_auto_create_on(self):
        user = User.objects.create(username='test')
        participant(user=user).enroll('test_experiment_x', alternatives=['other'])
        self.assertTrue(Experiment.objects.filter(name="test_experiment_x").exists())
