from django.contrib.auth.models import User
from django.template import Template, Context
from django.test import TestCase, override_settings, RequestFactory
from jinja2 import TemplateSyntaxError
from mock import (
    ANY,
    call,
    MagicMock,
    patch,
)

from experiments.models import Experiment
from experiments.templatetags.experiments import (
    ExperimentsExtension,
    _parse_token_contents,
)
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


class MockTokenStream:
    current = None
    _generator = None
    _tokens = []

    def __init__(self, tokens):
        self._tokens = tokens[:]
        self._generator = self._generator_foo()
        next(self._generator)

    def _generator_foo(self):
        for token in self._tokens:
            self.current = MagicMock(**token)
            yield self.current
        raise StopIteration

    def __next__(self):
        return next(self._generator)

    def skip_if(self, token_type):
        should_skip = self.current.type == token_type
        if should_skip:
            next(self._generator)
            return self.current
        return None


class ExperimentsJinjaExtensionTests(TestCase):
    def setUp(self):
        self.env = MagicMock()
        self.parser = MagicMock()
        self.extension = ExperimentsExtension(self.env)

    def test_parse(self):
        self.parser.stream.current.value = 'some_tag'
        self.extension.parse_some_tag = MagicMock()
        self.extension.parse(parser=self.parser)
        self.extension.parse_some_tag.assert_called_once_with(self.parser)

    def test_parse_experiment(self):

        mock_stream = MockTokenStream([
            {'type': 'string', 'value': 'some_experiment', 'lineno': 123},
            {'type': 'comma'},
            {'type': 'string', 'value': 'some_alternative'},
            {'type': 'block_end'},
        ])
        self.parser.stream = mock_stream
        self.extension.call_method = MagicMock()
        self.extension.parse_experiment(self.parser)

        self.extension.call_method.assert_called_once_with(
            'render_experiment', ANY, lineno=123)

    def test_parse_experiment_too_few_args(self):

        mock_stream = MockTokenStream([
            {'type': 'string', 'value': 'some_experiment', 'lineno': 123},
            {'type': 'block_end'},
        ])
        self.parser.stream = mock_stream
        self.extension.call_method = MagicMock()
        with self.assertRaises(TemplateSyntaxError):
            self.extension.parse_experiment(self.parser)
        self.extension.call_method.assert_not_called()

    @patch('experiments.templatetags.experiments.participant')
    @patch('experiments.templatetags.experiments.experiment_manager')
    def test_render_experiment(self, experiment_manager, participant):
        request = MagicMock()
        user = MagicMock(
            is_enrolled=MagicMock(return_value=True),
        )
        experiment_name = 'some_experiment'
        alternative = 'some_alternative'
        weight = 1
        user_variable = None
        context = {
            'request': request,
        }
        caller = MagicMock()
        experiment = MagicMock()
        experiment_manager.get_experiment.return_value = experiment
        participant.return_value = user

        retval = self.extension.render_experiment(
            experiment_name, alternative, weight, user_variable,
            context, caller)

        experiment_manager.get_experiment.assert_called_once_with(
            experiment_name)
        experiment.ensure_alternative_exists.assert_called_once_with(
            alternative, weight)
        participant.assert_called_once_with(request)
        user.is_enrolled.assert_called_once_with(experiment_name, alternative)
        self.assertEqual(retval, caller.return_value)

    @patch('experiments.templatetags.experiments.participant')
    @patch('experiments.templatetags.experiments.experiment_manager')
    def test_render_experiment_specific_user(
            self, experiment_manager, participant):
        user = MagicMock(
            is_enrolled=MagicMock(return_value=False),
        )
        experiment_name = 'some_experiment'
        alternative = 'some_alternative'
        weight = 1
        user_variable = 'user'
        context = {
            'user': user,
        }
        caller = MagicMock()
        experiment = MagicMock()
        experiment_manager.get_experiment.return_value = experiment
        participant.return_value = user

        retval = self.extension.render_experiment(
            experiment_name, alternative, weight, user_variable,
            context, caller)

        experiment_manager.get_experiment.assert_called_once_with(
            experiment_name)
        experiment.ensure_alternative_exists.assert_called_once_with(
            alternative, weight)
        participant.assert_called_once_with(user=user)
        user.is_enrolled.assert_called_once_with(experiment_name, alternative)
        caller.assert_not_called()
        self.assertEqual(str(retval), '')

    @patch('experiments.templatetags.experiments.nodes')
    def test_parse_experiments_confirm_human(self, nodes):
        mock_stream = MockTokenStream([
            {'type': 'block_end', 'lineno': 123},
        ])
        self.parser.stream = mock_stream
        self.extension.call_method = MagicMock()

        self.extension.parse_experiments_confirm_human(self.parser)

        nodes.ContextReference.assert_called_once_with()
        args = [nodes.ContextReference.return_value, ]
        self.extension.call_method.assert_called_once_with(
            'render_experiments_confirm_human', args, lineno=123)

    @patch('experiments.templatetags.experiments._experiments_confirm_human')
    @patch('experiments.templatetags.experiments.template.loader.get_template')
    def test_render_experiments_confirm_human(
            self, get_template, _experiments_confirm_human):
        caller = MagicMock()
        context = {'some': 'vars'}
        tmplt = get_template.return_value
        _experiments_confirm_human.return_value = {'moar': 'vars'}
        context2 = {
            'some': 'vars',
            'moar': 'vars',
        }

        retval = self.extension.render_experiments_confirm_human(
            context, caller)

        get_template.assert_called_once_with('experiments/confirm_human.html')
        self.assertEqual(retval, tmplt.render.return_value)
        tmplt.render.assert_called_once_with(context2)

    @patch('experiments.templatetags.experiments.nodes')
    def test_parse_experiment_goal(self, nodes):
        mock_stream = MockTokenStream([
            {'type': 'string', 'value': 'some_goal', 'lineno': 123},
            {'type': 'block_end'},
        ])
        self.parser.stream = mock_stream
        self.extension.call_method = MagicMock()

        self.extension.parse_experiment_goal(self.parser)

        nodes.ContextReference.assert_called_once_with()
        nodes.Const.assert_called_once_with('some_goal')
        const_node = nodes.Const.return_value
        args = [nodes.ContextReference.return_value, const_node]
        self.extension.call_method.assert_called_once_with(
            'render_experiment_goal', args, lineno=123)

    @patch('experiments.templatetags.experiments._experiment_goal')
    @patch('experiments.templatetags.experiments.template.loader.get_template')
    def test_render_experiment_goal(
            self, get_template, _experiment_goal):
        caller = MagicMock()
        context = {'some': 'vars'}
        goal_name = 'some_goal'
        tmplt = get_template.return_value
        _experiment_goal.return_value = {'moar': 'vars'}
        context2 = {
            'some': 'vars',
            'moar': 'vars',
        }

        retval = self.extension.render_experiment_goal(
            context, goal_name, caller)

        get_template.assert_called_once_with('experiments/goal.html')
        self.assertEqual(retval, tmplt.render.return_value)
        tmplt.render.assert_called_once_with(context2)

    @patch('experiments.templatetags.experiments.nodes')
    def test_parse_experiment_enroll_strings_only(self, nodes):
        mock_stream = MockTokenStream([
            {'type': 'string', 'value': 'some_experiment', 'lineno': 123},
            {'type': 'string', 'value': 'alternative1'},
            {'type': 'string', 'value': 'alternative2'},
            {'type': 'as'},
            {'type': 'name', 'value': 'name_for_assignment'},
            {'type': 'block_end'},
        ])
        self.parser.stream = mock_stream
        self.extension.call_method = MagicMock()
        target = self.parser.parse_assign_target.return_value
        experiment_name_node = MagicMock()
        alternative1_node = MagicMock()
        alternative2_node = MagicMock()
        nodes.Const.side_effect = [
            experiment_name_node,
            alternative1_node,
            alternative2_node,
        ]
        alternatives_list = nodes.List.return_value

        retval = self.extension.parse_experiment_enroll(self.parser)

        nodes.Const.assert_has_calls([
            call('some_experiment'),
            call('alternative1'),
            call('alternative2'),
        ])
        nodes.List.assert_called_once_with(
            [alternative1_node, alternative2_node])
        nodes.ContextReference.assert_called_once_with()
        ctx_node = nodes.ContextReference.return_value
        args = [experiment_name_node, alternatives_list, ctx_node]
        self.extension.call_method.assert_called_once_with(
            'render_experiment_enroll', args, lineno=123,
        )
        call_node = self.extension.call_method.return_value
        self.parser.parse_assign_target.assert_called_once_with()
        assignment_node = nodes.Assign.return_value
        nodes.Assign.assert_called_once_with(target, call_node, lineno=123)
        self.assertEqual(retval, assignment_node)

    @patch('experiments.templatetags.experiments.nodes')
    def test_parse_experiment_enroll_wrong_syntax(self, nodes):
        mock_stream = MockTokenStream([
            {'type': 'string', 'value': 'some_experiment', 'lineno': 123},
            {'type': 'string', 'value': 'alternative1'},
            {'type': 'string', 'value': 'alternative2'},
            {'type': 'block_end'},
        ])
        self.parser.stream = mock_stream

        with self.assertRaises(TemplateSyntaxError):
            self.extension.parse_experiment_enroll(self.parser)

        nodes.Assign.assert_not_called()

    @patch('experiments.templatetags.experiments._experiment_enroll')
    def test_render_experiment_enroll(self, _experiment_enroll):
        context = {'some': 'vars'}
        experiment_name = 'some_experiment'
        alternatives = ['alt1', 'alt2']
        enrolled = _experiment_enroll.return_value

        retval = self.extension.render_experiment_enroll(
            experiment_name, alternatives, context)

        self.assertEqual(retval, enrolled)

    @patch('experiments.templatetags.experiments.nodes')
    def test_name_or_const_with_name(self, nodes):
        token = MagicMock(type='name', value='some_name')

        retval = self.extension._name_or_const(token)

        self.assertEqual(retval, nodes.Name.return_value)
        nodes.Name.assert_called_once_with('some_name', 'load')

    @patch('experiments.templatetags.experiments.nodes')
    def test_name_or_const_with_string(self, nodes):
        token = MagicMock(type='string', value='some_value')

        retval = self.extension._name_or_const(token)

        self.assertEqual(retval, nodes.Const.return_value)
        nodes.Const.assert_called_once_with('some_value')

    def test_name_or_const_with_other(self):
        token = MagicMock(type='other')

        with self.assertRaises(ValueError):
            self.extension._name_or_const(token)

    def test_token_as_with_name(self):
        mock_stream = MockTokenStream([
            {'type': 'name', 'value': 'as'},
        ])
        self.parser.stream = mock_stream
        retval = self.extension._token_as(self.parser)
        self.assertTrue(retval)

    def test_token_as_with_as(self):
        mock_stream = MockTokenStream([
            {'type': 'as'},
        ])
        self.parser.stream = mock_stream
        retval = self.extension._token_as(self.parser)
        self.assertTrue(retval)

    def test_token_as_with_other(self):
        mock_stream = MockTokenStream([
            {'type': 'other'},
        ])
        self.parser.stream = mock_stream
        retval = self.extension._token_as(self.parser)
        self.assertFalse(retval)
