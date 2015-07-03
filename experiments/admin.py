from django.contrib import admin
from django.contrib.admin.utils import unquote
from experiments.admin_utils import get_result_context
from experiments.models import Experiment
from experiments import conf


class ExperimentAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'state')
    list_filter = ('state',)
    ordering = ('-start_date',)
    search_fields = ('name',)
    actions = None
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'start_date', 'end_date', 'state'),
        }),
        ('Relevant Goals', {
            'classes': ('collapse', 'hidden-relevant-goals'),
            'fields': ('relevant_chi2_goals', 'relevant_mwu_goals'),
        })
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            # Cannot edit the name after creating the experiment
            return ['name', 'start_date', 'end_date']
        return ['start_date', 'end_date']

    def add_view(self, request, form_url='', extra_context=None):
        context = {}
        if extra_context:
            context.update(extra_context)
        context.update({
            'all_goals': conf.ALL_GOALS,
        })
        return super(ExperimentAdmin, self).add_view(request, form_url=form_url, extra_context=context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        experiment = self.get_object(request, unquote(object_id))

        context = {}
        if extra_context:
            context.update(extra_context)
        context.update({
            'all_goals': conf.ALL_GOALS,
        })
        context.update(get_result_context(request, experiment))
        return super(ExperimentAdmin, self).change_view(request, object_id, form_url=form_url, extra_context=context)

admin.site.register(Experiment, ExperimentAdmin)

