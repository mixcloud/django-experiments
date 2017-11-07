# coding=utf-8
from __future__ import absolute_import

from unittest import TestCase

try:
    from unittest import mock
except ImportError:
    import mock

from ..models import AdminConditional
from ...models import (
    ENABLED_STATE,
    Experiment,
    CONTROL_STATE,
)


class ConditionalEnrollmentTestCase(TestCase):

    def setUp(self):
        self.conditional_true = AdminConditional(
            template='true',
        )
        self.conditional_false = AdminConditional(
            template='no no no',
        )
        self.experiment = Experiment.objects.create(
            name='automatic_experiment',
            alternatives={
                'control': 'stuff',
                'variant_1': 'stuff',
            },
            state=ENABLED_STATE,
            auto_enroll=True,
        )
        self.request = mock.MagicMock()

    def tearDown(self):
        if self.conditional_false.id:
            self.conditional_false.delete()
        if self.conditional_true.id:
            self.conditional_true.delete()
        self.experiment.delete()

    def test_should_ot_enroll_set_to_false(self):
        self.experiment.auto_enroll = False
        self.experiment.save()
        value = self.experiment.should_auto_enroll(self.request)
        self.assertFalse(value)

    def test_should_enroll_single_condition(self):
        self.conditional_true.experiment = self.experiment
        self.conditional_true.save()
        value = self.experiment.should_auto_enroll(self.request)
        self.assertTrue(value)

    def test_should_not_enroll_single_condition(self):
        self.conditional_false.experiment = self.experiment
        self.conditional_false.save()
        value = self.experiment.should_auto_enroll(self.request)
        self.assertFalse(value)

    def test_should_enroll_multiple_conditions(self):
        self.conditional_false.experiment = self.experiment
        self.conditional_false.save()
        self.conditional_true.experiment = self.experiment
        self.conditional_true.save()
        value = self.experiment.should_auto_enroll(self.request)
        self.assertTrue(value)

    def test_should_not_enroll_no_alternatives(self):
        self.conditional_true.experiment = self.experiment
        self.conditional_true.save()
        self.experiment.alternatives = {}
        self.experiment.save()
        value = self.experiment.should_auto_enroll(self.request)
        self.assertFalse(value)

    def test_should_not_enroll_no_conditionals(self):
        value = self.experiment.should_auto_enroll(self.request)
        self.assertFalse(value)

    def test_should_not_enroll_disabled(self):
        self.experiment.state = CONTROL_STATE
        self.experiment.save()
        value = self.experiment.should_auto_enroll(self.request)
        self.assertFalse(value)
