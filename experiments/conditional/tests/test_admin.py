# coding=utf-8
from __future__ import absolute_import

from unittest import TestCase

from django.core.exceptions import ValidationError
from experiments.conditional.models import AdminConditionalTemplate, \
    AdminConditional

from experiments.conditional.admin import AdminConditionalForm

from experiments.tests.testing_2_3 import mock


def mock_super_init(self, *a, **kw):
    self.instance = kw['instance']
    self.fields = kw['fields']


@mock.patch('experiments.conditional.admin.forms.ModelForm.__init__',
            new=mock_super_init)
class AdminConditionalFormTestCase(TestCase):

    def test_init_set_required_fields_is_new(self):
        mock_fields = mock.MagicMock()
        instance = mock.MagicMock()
        instance.pk = None
        form = AdminConditionalForm(instance=instance, fields=mock_fields)
        self.assertTrue(form.fields['copy_from'].required)

    def test_init_set_required_fields_not_new(self):
        mock_fields = mock.MagicMock()
        instance = mock.MagicMock()
        instance.pk = 123
        form = AdminConditionalForm(instance=instance, fields=mock_fields)
        self.assertTrue(form.fields['description'].required)
        self.assertTrue(form.fields['template'].required)

    def test_clean_context_code_bad_code(self):
        instance = mock.MagicMock()
        mock_fields = mock.MagicMock()
        cleaned_data = {
            'context_code': 'MAIN:\n\tGOTO MAIN\n'
        }
        form = AdminConditionalForm(instance=instance, fields=mock_fields)
        form.cleaned_data = cleaned_data
        with self.assertRaises(ValidationError):
            form.clean_context_code()

    def test_clean_context_code_good_code(self):
        instance = mock.MagicMock()
        mock_fields = mock.MagicMock()
        cleaned_data = {
            'context_code': 'a = 42\n'
        }
        form = AdminConditionalForm(instance=instance, fields=mock_fields)
        form.cleaned_data = cleaned_data
        value = form.clean_context_code()
        self.assertEqual(value, 'a = 42\n')

    @mock.patch('django.forms.ModelForm.save')
    def test_save_new_instance(self, super_save):
        template_instance = AdminConditionalTemplate(
            description='some conditional',
            template='da template',
            context_code='import this'
        )
        instance = AdminConditional(
            copy_from=template_instance,
        )
        mock_fields = mock.MagicMock()
        cleaned_data = {
            'copy_from': template_instance,
        }
        form = AdminConditionalForm(instance=instance, fields=mock_fields)
        form.cleaned_data = cleaned_data
        value = form.save(commit=True)
        self.assertEqual(instance.description, 'some conditional')
        self.assertEqual(instance.template, 'da template')
        self.assertEqual(instance.context_code, 'import this')
        super_save.assert_called_once_with(commit=True)
        self.assertEqual(value, super_save.return_value)

    @mock.patch('django.forms.ModelForm.save')
    def test_save_not_new_instance(self, super_save):
        template_instance = AdminConditionalTemplate(
            description='some conditional',
            template='da template',
            context_code='import this'
        )
        instance = AdminConditional(
            copy_from=template_instance,
            description='some other conditional',
            template='da edited template',
            context_code='from __future__ import braces',
            pk=123,
        )
        mock_fields = mock.MagicMock()
        cleaned_data = {
            'copy_from': template_instance,
        }
        form = AdminConditionalForm(instance=instance, fields=mock_fields)
        form.cleaned_data = cleaned_data
        value = form.save(commit=True)
        self.assertEqual(instance.description, 'some other conditional')
        self.assertEqual(instance.template, 'da edited template')
        self.assertEqual(instance.context_code, 'from __future__ import braces')
        super_save.assert_called_once_with(commit=True)
        self.assertEqual(value, super_save.return_value)
