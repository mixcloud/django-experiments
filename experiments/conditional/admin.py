# coding=utf-8
from __future__ import absolute_import

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import (
    AdminConditional,
    AdminConditionalTemplate,
)


class AdminConditionalForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(AdminConditionalForm, self).__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['copy_from'].required = True
            self.fields['copy_from'].label = 'Template'
            self.fields['copy_from'].help_text = (
                'Save the experiment to be able to configure new conditionals')
        else:
            self.fields['description'].required = True
            self.fields['template'].required = True

    def clean_context_code(self):
        try:
            AdminConditional._eval_context_code(
                self.cleaned_data['context_code'],
                fail_silently=False,
            )
        except Exception as e:
            msg = AdminConditional._syntax_error_msg(e)
            raise ValidationError(msg)
        return self.cleaned_data['context_code']

    def save(self, commit=True):
        if not self.instance.pk:
            conditional_template = self.cleaned_data['copy_from']
            self.instance.description = conditional_template.description
            self.instance.template = conditional_template.template
            self.instance.context_code = conditional_template.context_code
        return super(AdminConditionalForm, self).save(commit=commit)

    class Meta:
        model = AdminConditional
        fields = (
            'copy_from',
            'description',
            'template',
            "context_code",
        )


class AdminConditionalInline(admin.StackedInline):
    model = AdminConditional
    form = AdminConditionalForm
    extra = 0
    fields = AdminConditionalForm.Meta.fields


@admin.register(AdminConditionalTemplate)
class AdminConditionalTemplateAdmin(admin.ModelAdmin):
    fields = (
        'description',
        'template',
        'context_code',
    )
