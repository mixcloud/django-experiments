# coding=utf-8
from __future__ import absolute_import

from unittest import TestCase

from experiments.conditional.templatetags.experiments import _auto_enroll, \
    experiments_auto_enroll, AutoEnrollExperimentsExtension
from experiments.tests.testing_2_3 import mock


class DjangoTemplateTagTestCase(TestCase):

    def setUp(self):
        self.request = mock.MagicMock()
        self.context = {'request': self.request}

    @mock.patch('experiments.conditional.templatetags.experiments.Experiments',
                autospec=True)
    def test_auto_enroll_anonymous(self, Experiments):
        self.request.user.is_staff = False
        instance = Experiments.return_value
        value = _auto_enroll(self.context)
        expected_value = ''
        self.assertEqual(expected_value, value)
        Experiments.assert_called_once_with(self.context)
        instance.conditionally_enroll.assert_called_once_with()

    @mock.patch('experiments.conditional.templatetags.experiments.Experiments',
                autospec=True)
    def test_auto_enroll_staff(self, Experiments):
        self.request.user.is_staff = True
        instance = Experiments.return_value
        instance.report = {'mock': 'report'}
        value = _auto_enroll(self.context)
        expected_value = (
            '<script>window.ca_experiments = {"mock": "report"};</script>')
        self.assertEqual(expected_value, value)
        Experiments.assert_called_once_with(self.context)
        Experiments.return_value.conditionally_enroll.assert_called_once_with()

    @mock.patch(
        'experiments.conditional.templatetags.experiments._auto_enroll')
    def test_template_tag(self, _auto_enroll):
        rendered_value = experiments_auto_enroll(self.context)
        _auto_enroll.assert_called_once_with(self.context)
        self.assertEqual(rendered_value, _auto_enroll.return_value)


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
            self.current = mock.MagicMock(**token)
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
        self.env = mock.MagicMock()
        self.parser = mock.MagicMock()
        self.parser.stream.__iter__ = mock.MagicMock()
        self.parser.stream.__next__ = mock.MagicMock()
        self.extension = AutoEnrollExperimentsExtension(self.env)

    def test_attributes(self):
        expected_tags = {'experiments_auto_enroll',}
        self.assertEqual(expected_tags, self.extension.tags)
        for tag in expected_tags:
            self.assertTrue(hasattr(self.extension, 'parse_{}'.format(tag)))
            self.assertTrue(hasattr(self.extension, 'render_{}'.format(tag)))

    def test_parse(self):
        self.parser.stream.current.value = 'some_tag'
        self.extension.parse_some_tag = mock.MagicMock()
        self.extension.parse(parser=self.parser)
        self.extension.parse_some_tag.assert_called_once_with(self.parser)

    def test_parse_experiments_auto_enroll(self):
        mock_stream = MockTokenStream([
            {'type': 'string', 'value': 'some_experiment', 'lineno': 123},
            {'type': 'block_end'},
        ])
        self.parser.stream = mock_stream
        self.extension.call_method = mock.MagicMock()
        self.extension.parse_experiments_auto_enroll(self.parser)
        self.extension.call_method.assert_called_once_with(
            'render_experiments_auto_enroll', mock.ANY, lineno=123)

    @mock.patch(
        'experiments.conditional.templatetags.experiments.nodes')
    @mock.patch(
        'experiments.conditional.templatetags.experiments._auto_enroll')
    def test_render_experiments_auto_enroll(self, _auto_enroll, nodes):
        caller = mock.MagicMock()
        context = {'some': 'vars'}
        _auto_enroll.return_value = 'mock script'

        value = self.extension.render_experiments_auto_enroll(
            context, caller)

        _auto_enroll.assert_called_once_with({'some': 'vars'})
        nodes.Markup.assert_called_once_with('mock script')
        self.assertEqual(value, nodes.Markup.return_value)
