# coding=utf-8
from __future__ import absolute_import

from django import forms
from django.contrib import admin

from .models import (
    AdminConditional,
    AdminConditionalTemplate,
)


class AdminConditionalForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(AdminConditionalForm, self).__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['copy_from'].required = True
        else:
            self.fields['description'].required = True
            self.fields['template'].required = True

    def save(self, commit=True):
        if not self.instance.pk:
            template_pk = self.cleaned_data['copy_from']
            conditional_template = AdminConditionalTemplate.objects.get(
                pk=template_pk)
            self.instance.description = conditional_template.description
            self.instance.template = conditional_template.template
        return super(AdminConditionalForm, self).save(commit)

    class Meta:
        model = AdminConditional


class AdminConditionalInline(admin.StackedInline):
    model = AdminConditional
    #form = AdminConditionalForm
    extra = 0
    fields = (
        'copy_from',
        'description',
        'template',
        'template_values',
    )


@admin.register(AdminConditionalTemplate)
class AdminConditionalTemplateAdmin(admin.ModelAdmin):
    pass
