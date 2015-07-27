from django.contrib import admin
from django.contrib.admin.utils import unquote
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.utils import timezone
from experiments.admin_utils import get_result_context
from experiments.models import Experiment
from experiments import conf
from django.conf.urls import url
from experiments.utils import participant


class ExperimentAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'state')
    list_filter = ('state', 'start_date', 'end_date')
    ordering = ('-start_date',)
    search_fields = ('=name',)
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
        readonly_fields = ['start_date', 'end_date']
        if obj:
            # Cannot edit the name after creating the experiment
            return ['name'] + readonly_fields
        return readonly_fields

    # --------------------------------------- Overriding admin views

    class Media:
        css = {
            "all": (
                'experiments/css/admin.css',
            ),
        }
        js = (
            'https://www.google.com/jsapi',  # used for charts
            'experiments/js/csrf.js',
            'experiments/js/admin.js',
        )

    def _admin_view_context(self, extra_context=None):
        context = {}
        if extra_context:
            context.update(extra_context)
        context['all_goals'] = conf.ALL_GOALS
        return context

    def add_view(self, request, form_url='', extra_context=None):
        return super(ExperimentAdmin, self).add_view(request,
                                                     form_url=form_url,
                                                     extra_context=self._admin_view_context(extra_context=extra_context))

    def change_view(self, request, object_id, form_url='', extra_context=None):
        experiment = self.get_object(request, unquote(object_id))
        context = self._admin_view_context(extra_context=extra_context)
        context.update(get_result_context(request, experiment))
        return super(ExperimentAdmin, self).change_view(request, object_id, form_url=form_url, extra_context=context)

    # --------------------------------------- Views for ajax functionality

    def get_urls(self):
        experiment_urls = [
            url(r'^set-alternative/$', self.admin_site.admin_view(self.set_alternative_view), name='experiment_admin_set_alternative'),
            url(r'^set-state/$', self.admin_site.admin_view(self.set_state_view), name='experiment_admin_set_state'),
        ]
        return experiment_urls + super(ExperimentAdmin, self).get_urls()

    def set_alternative_view(self, request):
        """
        Allows the admin user to change their assigned alternative
        """
        if not request.user.has_perm('experiments.change_experiment'):
            return HttpResponseForbidden()

        experiment_name = request.POST.get("experiment")
        alternative_name = request.POST.get("alternative")
        if not (experiment_name and alternative_name):
            return HttpResponseBadRequest()

        participant(request).set_alternative(experiment_name, alternative_name)
        return JsonResponse({
            'success': True,
            'alternative': participant(request).get_alternative(experiment_name)
        })

    def set_state_view(self, request):
        """
        Changes the experiment state
        """
        if not request.user.has_perm('experiments.change_experiment'):
            return HttpResponseForbidden()

        try:
            state = int(request.POST.get("state", ""))
        except ValueError:
            return HttpResponseBadRequest()

        try:
            experiment = Experiment.objects.get(name=request.POST.get("experiment"))
        except Experiment.DoesNotExist:
            return HttpResponseBadRequest()

        experiment.state = state

        if state == 0:
            experiment.end_date = timezone.now()
        else:
            experiment.end_date = None

        experiment.save()

        return HttpResponse()

admin.site.register(Experiment, ExperimentAdmin)

