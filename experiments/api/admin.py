# coding=utf-8
import logging

from django.contrib import admin

from .models import RemoteExperiment


_all__ = (
    'RemoteExperimentAdmin',
)


logger = logging.getLogger(__file__)


@admin.register(RemoteExperiment)
class RemoteExperimentAdmin(admin.ModelAdmin):
    list_display = (
        'admin_link',
        'site',
        'state',
        'start_date',
        'end_date',
    )
    list_display_links = None
    list_filter = (
        'site',
        'state',
    )
    search_fields = (
        'name',
    )

    def admin_link(self, obj):
        return '<a href="{admin_url}" target="_blank">{name}</a>'.format(
            admin_url=obj.admin_url,
            name=obj.name,
        )
    admin_link.short_description = 'name'
    admin_link.allow_tags = True
    admin_link.admin_order_field = 'name'

    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_add_permission(self, request):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def changelist_view(self, request, extra_context=None):
        excs = RemoteExperiment.update_remotes()
        for e in excs:
            self.message_user(
                request, 'Error updating from {site}: {e}'.format(
                    site=e.server['url'],
                    e=e.original_exception,
                ))
        return super(RemoteExperimentAdmin, self).changelist_view(
            request, extra_context)
