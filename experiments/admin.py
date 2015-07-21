from django.contrib import admin
from django.contrib.admin.utils import unquote
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.utils import timezone
from experiments.admin_utils import get_result_context
from experiments.models import Experiment
from experiments import conf
from django.conf.urls import url
from experiments.utils import participant


class ExperimentAdmin(admin.ModelAdmin):
    class Media:
        css = {
            "all": (
                'experiments/css/admin.css',
            ),
        }
        js = (
            'experiments/js/admin.js',
        )

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

    def get_urls(self):
        urls = super(ExperimentAdmin, self).get_urls()
        experiment_urls = [
            url(r'^set-alternative/$', self.admin_site.admin_view(self.set_alternative), name='experiment_admin_set_alternative'),
            url(r'^set-state/$', self.admin_site.admin_view(self.set_state), name='experiment_admin_set_state'),
        ]
        return experiment_urls + urls

    def set_alternative(self, request):
        experiment_name = request.POST.get("experiment")
        alternative_name = request.POST.get("alternative")
        participant(request).set_alternative(experiment_name, alternative_name)
        return JsonResponse({
            'success': True,
            'alternative': participant(request).get_alternative(experiment_name)
        })

    def set_state(self, request):
        try:
            state = int(request.POST.get("state"))
        except ValueError:
            return HttpResponseBadRequest()

        experiment = Experiment.objects.get(name=request.POST.get("experiment"))
        experiment.state = state

        if state == 0:
            experiment.end_date = timezone.now()
        else:
            experiment.end_date = None

        experiment.save()

        return HttpResponse()

admin.site.register(Experiment, ExperimentAdmin)

