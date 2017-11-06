# coding=utf-8
from __future__ import absolute_import

from unittest import TestCase


try:
    from unittest import mock
except ImportError:
    import mock

from ..views import (
    Experiments,
    ExperimentsMixin,
)
from ...models import (
    CONTROL_STATE,
    Experiment,
    ENABLED_STATE,
)

class MockBaseView(mock.MagicMock):

    def dispatch(self, request, *args, **kwargs):
        pass


class ExperimentsMixinTestCase(TestCase):

    def setUp(self):

        class MockView(ExperimentsMixin, MockBaseView):
            pass

        self.view = MockView()
        self.request = mock.MagicMock()
        self.response = mock.MagicMock()

    def test_initialize_experiments_mixin(self):
        with mock.patch.object(MockBaseView, 'dispatch') as super_dispatch:
            super_dispatch.return_value = self.response
            response = self.view.dispatch(self.request)
            self.assertIs(response, self.response)
            super_dispatch.assert_called_once_with(self.request)


class ExperimentsTestCase(TestCase):

    def setUp(self):

        class MockView(ExperimentsMixin, MockBaseView):
            pass

        self.view = MockView()
        self.request = mock.MagicMock()
        self.response = mock.MagicMock()

    def tearDown(self):
        Experiment.objects.all().delete()

    def test_no_experiments(self):
        instance = Experiments(self.request, self.view)
        with mock.patch('experiments.models'
                        '.Experiment.should_auto_enroll') as sae:
            instance.conditionally_enroll()
            sae.assert_not_called()

    def test_wo_auto_enrollable_experiments(self):
        Experiment.objects.create(
            name="some_experiment",
            state=ENABLED_STATE,
            auto_enroll=False,
        )
        instance = Experiments(self.request, self.view)
        with mock.patch('experiments.models'
                        '.Experiment.should_auto_enroll') as sae:
            instance.conditionally_enroll()
            sae.assert_not_called()

    @mock.patch('experiments.utils.participant')
    def test_w_auto_enrollable_experiment(self, participant):
        Experiment.objects.create(
            name="some_experiment",
            state=ENABLED_STATE,
            auto_enroll=True,
        )
        instance = Experiments(self.request, self.view)
        with mock.patch(
                'experiments.models.Experiment.should_auto_enroll') as sae:
            sae.return_value = False
            instance.conditionally_enroll()
            sae.assert_called_once_with(self.request)
        participant.assert_called_once_with(self.request)

    @mock.patch('experiments.utils.participant')
    def test_w_auto_enrollable_inactive_experiment(self, participant):
        Experiment.objects.create(
            name="some_experiment",
            state=CONTROL_STATE,
            auto_enroll=True,
        )
        instance = Experiments(self.request, self.view)
        with mock.patch(
                'experiments.models.Experiment.should_auto_enroll') as sae:
            sae.return_value = True
            instance.conditionally_enroll()
            sae.assert_called_once_with(self.request)
        participant.assert_called_once_with(self.request)


class ExperimentsContextTestCase(TestCase):

    def setUp(self):
        self.view = mock.MagicMock()
        self.request = mock.MagicMock()
        self.instance = Experiments(self.request, self.view)

        class A(object):
            b = "B"
            def foo(self):
                return 'bar'
            @property
            def prop(self):
                return 123

        self.a = A()

    def test_add_method_to_context(self):
        self.instance._add_to_context(self.a, 'foo')
        self.assertNotIn('foo', self.instance.context)
        value = self.a.foo()
        self.assertEqual(value, 'bar')
        self.assertEqual(self.instance.context['foo'], 'bar')

    def test_add_unknown_method_to_context(self):
        self.instance._add_to_context(self.a, 'bar')
        self.assertNotIn('foo', self.instance.context)
        with self.assertRaises(AttributeError):
            self.a.bar()
        self.assertNotIn('foo', self.instance.context)

    def test_add_attribute_to_context(self):
        self.instance._add_to_context(self.a, 'b')
        self.assertIn('b', self.instance.context)
        self.assertEqual(self.instance.context['b'], 'B')
        value = self.a.b
        self.assertEqual(value, 'B')

    def test_add_property_to_context(self):
        self.instance._add_to_context(self.a, 'prop')
        self.assertIn('prop', self.instance.context)
        self.assertEqual(self.instance.context['prop'], 123)
        value = self.a.prop
        self.assertEqual(value, 123)
