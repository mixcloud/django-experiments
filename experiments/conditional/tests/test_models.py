# coding=utf-8
from __future__ import absolute_import

from unittest import TestCase

from django.template import TemplateSyntaxError
from django.test import override_settings
from lxml.etree import XMLSyntaxError

from experiments.tests.testing_2_3 import mock

from experiments.models import (
    ENABLED_STATE,
    Experiment,
)
from experiments.conditional.models import (
    AdminConditional,
    AdminConditionalTemplate,
)


class ConditionalEnrollmentTestCase(TestCase):

    def setUp(self):
        self.conditional_true = AdminConditional(
            template='<true />',
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
        )
        self.request = mock.MagicMock()

    def tearDown(self):
        if self.conditional_false.id:
            self.conditional_false.delete()
        if self.conditional_true.id:
            self.conditional_true.delete()
        self.experiment.delete()

    def test_is_enabled_by_conditionals_single_condition(self):
        self.conditional_true.experiment = self.experiment
        self.conditional_true.save()
        value = self.experiment.is_enabled_by_conditionals(self.request)
        self.assertTrue(value)

    def test_is_enabled_by_conditionals_single_condition(self):
        self.conditional_false.experiment = self.experiment
        self.conditional_false.save()
        value = self.experiment.is_enabled_by_conditionals(self.request)
        self.assertFalse(value)

    def test_is_enabled_by_conditionals_multiple_conditions(self):
        self.conditional_false.experiment = self.experiment
        self.conditional_false.save()
        self.conditional_true.experiment = self.experiment
        self.conditional_true.save()
        value = self.experiment.is_enabled_by_conditionals(self.request)
        self.assertTrue(value)

    def test_is_enabled_by_conditionals_no_conditionals(self):
        value = self.experiment.is_enabled_by_conditionals(self.request)
        self.assertTrue(value)


class ConditionalTemplatesCodeTestCase(TestCase):

    def test_missing_vars_in_code(self):
        conditional_template = AdminConditionalTemplate(
            template=(
                '{% if <<a>> == 42 %}<true />{% else %}<false />{% endif %}'),
            context_code=None,
        )
        conditional_template.save()
        self.assertEqual(conditional_template.context_code, 'a = None\n')
        conditional_template = AdminConditionalTemplate.objects.get(
            pk=conditional_template.pk)
        self.assertEqual(conditional_template.context_code, 'a = None\n')

    def test_missing_null_code(self):
        conditional_template = AdminConditionalTemplate(
            template='<true />',
            context_code=None,
        )
        conditional_template.save()
        self.assertEqual(conditional_template.context_code, '')
        conditional_template = AdminConditionalTemplate.objects.get(
            pk=conditional_template.pk)
        self.assertEqual(conditional_template.context_code, '')

    def test_missing_newline_at_the_end_of_code(self):
        conditional_template = AdminConditionalTemplate(
            template=(
                '{% if <<a>> == <<b>> %}<true />'
                '{% else %}<false />{% endif %}'),
            context_code='a = 41\nb=42',
        )
        conditional_template.save()
        self.assertEqual(conditional_template.context_code, 'a = 41\nb=42\n')
        conditional_template = AdminConditionalTemplate.objects.get(
            pk=conditional_template.pk)
        self.assertEqual(conditional_template.context_code, 'a = 41\nb=42\n')

    def test_a_fine_mix_of_stuffs(self):
        conditional_template = AdminConditionalTemplate(
            template=(
                '{% if <<a>> == <<b>> %}<true />'
                '{% else %}<false />{% endif %}'),
            context_code='\n\n#here be dragons!\n\nb = 42',
        )
        conditional_template.save()
        self.assertEqual(conditional_template.context_code,
                         '#here be dragons!\n\nb = 42\na = None\n')
        conditional_template = AdminConditionalTemplate.objects.get(
            pk=conditional_template.pk)
        self.assertEqual(conditional_template.context_code,
                         '#here be dragons!\n\nb = 42\na = None\n')


@mock.patch('experiments.conditional.models.logger')
class ConditionalTemplatesEvalTestCase(TestCase):

    def test_very_bad_code_silent(self, logger):
        really_bad_code = "for (i=0; i<10; i++){goto 100+i;}"
        value = AdminConditionalTemplate._eval_context_code(
            really_bad_code, fail_silently=True)
        self.assertEqual(value, {})
        logger.warning.assert_called_once_with(
            'invalid syntax, line 1: "for (i=0; i<10; i++){goto 100+i;}\n"')

    def test_very_bad_code_not_silent(self, logger):
        really_bad_code = "for (i=0; i<10; i++){goto 100+i;}"
        with self.assertRaises(SyntaxError):
            AdminConditionalTemplate._eval_context_code(
                really_bad_code, fail_silently=False)
        logger.warning.assert_not_called()

    def test_good_code(self, logger):
        good_code = (
            'a = 42\n'
            'b = "foo"\n'
            'c = ["zero", 2, 4]')
        value = AdminConditionalTemplate._eval_context_code(good_code)
        expected_value = {
            'a': 42,
            'b': 'foo',
            'c': ["zero", 2, 4],
        }
        self.assertEqual(value, expected_value)
        logger.warning.assert_not_called()


class AdminConditionalTestCase(TestCase):

    def setUp(self):
        self.experiment = Experiment(
            name='mock_experiment'
        )
        self.instance = AdminConditional(
            description='mock template',
            experiment=self.experiment,
        )
        self.request = mock.MagicMock()
        self.context = {'request': self.request}
        self.experiments = mock.MagicMock()
        self.experiments.context = self.context
        self.request.experiments = self.experiments

    def test_str(self):
        self.assertEqual(str(self.instance), 'mock template')

    def test_evaluate_true(self):
        self.context['object'] = {'id': 123}
        self.instance.template = (
            '<all_of>'
            '{% if <<a>> == 42 %}<true />{% else %}<false />{% endif %}'
            '{% if object.id == 123 %}<true />{% else %}<false />{% endif %}'
            '</all_of>')
        self.instance.context_code = 'a = 42'
        value = self.instance.evaluate(self.request)
        self.assertTrue(value)

    def test_evaluate_false_because_context_code(self):
        self.context['object'] = {'id': 123}
        self.instance.template = (
            '<all_of>'
            '{% if <<a>> == 42 %}<true />{% else %}<false />{% endif %}'
            '{% if object.id == 123 %}<true />{% else %}<false />{% endif %}'
            '</all_of>')
        self.instance.context_code = 'a = 41'
        value = self.instance.evaluate(self.request)
        self.assertFalse(value)

    def test_evaluate_false_because_template_context(self):
        self.context['object'] = {'id': 888}
        self.instance.template = (
            '<all_of>'
            '{% if <<a>> == 42 %}<true />{% else %}<false />{% endif %}'
            '{% if object.id == 123 %}<true />{% else %}<false />{% endif %}'
            '</all_of>')
        self.instance.context_code = 'a = 42'
        value = self.instance.evaluate(self.request)
        self.assertFalse(value)

    def test_evaluate_true_because_any(self):
        self.context['object'] = {'id': 888}
        self.instance.template = (
            '<any_of>'
            '{% if <<a>> == 42 %}<true />{% else %}<false />{% endif %}'
            '{% if object.id == 123 %}<true />{% else %}<false />{% endif %}'
            '</any_of>')
        self.instance.context_code = 'a = 42'
        value = self.instance.evaluate(self.request)
        self.assertTrue(value)

    @override_settings(DEBUG=False)
    @mock.patch('experiments.conditional.models.logger')
    def test_evaluate_false_because_xml_error(self, logger):
        self.context['object'] = {'id': 888}
        self.instance.template = (
            '<any_offfff ff f f f ff'
            '{% if <<a>> == 42 %}<true />{% else %}<false />{% endif %}'
            '{% if object.id == 123 %}<true />{% else %}<false />{% endif %}'
            '</any_of>')
        self.instance.context_code = 'a = 42'
        value = self.instance.evaluate(self.request)
        self.assertFalse(value)
        logger.exception.assert_called_once_with(
            'Error rendering conditional "mock template" '
            'for experiment "mock_experiment"')

    @override_settings(DEBUG=True)
    def test_evaluate_raises_because_xml_error(self):
        self.context['object'] = {'id': 888}
        self.instance.template = (
            '<any_offfff ff f f f ff'
            '{% if <<a>> == 42 %}<true />{% else %}<false />{% endif %}'
            '{% if object.id == 123 %}<true />{% else %}<false />{% endif %}'
            '</any_of>')
        self.instance.context_code = 'a = 42'
        with self.assertRaises(XMLSyntaxError):
            self.instance.evaluate(self.request)

    @override_settings(DEBUG=False)
    @mock.patch('experiments.conditional.models.logger')
    def test_evaluate_false_because_template_error(self, logger):
        self.context['object'] = {'id': 888}
        self.instance.template = (
            '<any_of>'
            '{% if <<a>> == 42 %%%%%%%}<true />{% else %}<false />{% endif %}'
            '{% if object.id == 123 %}<true />{% else %}<false />{% endif %}'
            '</any_of>')
        self.instance.context_code = 'a = 42'
        value = self.instance.evaluate(self.request)
        self.assertFalse(value)
        logger.exception.assert_called_once_with(
            'Error rendering conditional "mock template" '
            'for experiment "mock_experiment"')

    @override_settings(DEBUG=True)
    def test_evaluate_raises_because_template_error(self):
        self.context['object'] = {'id': 888}
        self.instance.template = (
            '<any_of>'
            '{% if <<a>> == 42 %%%%%%%}<true />{% else %}<false />{% endif %}'
            '{% if object.id == 123 %}<true />{% else %}<false />{% endif %}'
            '</any_of>')
        self.instance.context_code = 'a = 42'
        with self.assertRaises(TemplateSyntaxError):
            self.instance.evaluate(self.request)


class AdminConditionalTemplateTestCase(TestCase):

    def setUp(self):
        self.instance = AdminConditionalTemplate(
            description='mock template',
        )

    def test_str(self):
        self.assertEqual(str(self.instance), 'mock template')
