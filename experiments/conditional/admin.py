# coding=utf-8
from __future__ import absolute_import

from django.contrib import admin

from .models import (
    AdminConditional,
    AdminConditionalTemplate,
)


class AdminConditionalInline(admin.StackedInline):
    model = AdminConditional
    extra = 0


@admin.register(AdminConditionalTemplate)
class AdminConditionalTemplateAdmin(admin.ModelAdmin):
    pass
