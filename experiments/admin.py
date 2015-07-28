from django.contrib import admin
from django.contrib.admin.utils import unquote
from django import forms
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
    readonly_fields = ['start_date', 'end_date']

    def get_fieldsets(self, request, obj=None):
        """
        Slightly different fields are shown for Add and Change:
         - default_alternative can only be changed
         - name can only be set on Add
        """
        main_fields = ('description', 'start_date', 'end_date', 'state')

        if obj:
            main_fields += ('default_alternative',)
        else:
            main_fields = ('name',) + main_fields

        return (
            (None, {
                'fields': main_fields,
            }),
            ('Relevant Goals', {
                'classes': ('collapse', 'hidden-relevant-goals'),
                'fields': ('relevant_chi2_goals', 'relevant_mwu_goals'),
            })
        )

    # --------------------------------------- Default alternative

    def get_form(self, request, obj=None, **kwargs):
        """
        Add the default alternative dropdown with appropriate choices
        """
        if obj:
            if obj.alternatives:
                choices = [(alternative, alternative) for alternative in obj.alternatives.keys()]
            else:
                choices = [(conf.CONTROL_GROUP, conf.CONTROL_GROUP)]

            class ExperimentModelForm(forms.ModelForm):
                default_alternative = forms.ChoiceField(choices=choices,
                                                        initial=obj.default_alternative,
                                                        required=False)
            kwargs['form'] = ExperimentModelForm
        return super(ExperimentAdmin, self).get_form(request, obj=obj, **kwargs)

    def save_model(self, request, obj, form, change):
        if change:
            obj.set_default_alternative(form.cleaned_data['default_alternative'])
        obj.save()

    # --------------------------------------- Overriding admin views

    class Media:
        css = {
            "all": (
                'experiments/dashboard/css/admin.css',
            ),
        }
        js = (
            'https://www.google.com/jsapi',  # used for charts
            'experiments/dashboard/js/csrf.js',
            'experiments/dashboard/js/admin.js',
        )

    def _admin_view_context(self, extra_context=None):
        context = {}
        if extra_context:
            context.update(extra_context)
        context.update({
            'all_goals': conf.ALL_GOALS,
            'control_group': conf.CONTROL_GROUP,
        })
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

