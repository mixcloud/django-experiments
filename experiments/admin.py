# coding=utf-8
from __future__ import division
from django.contrib import admin
from django.contrib.admin.utils import unquote
from django import forms
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    JsonResponse,
)
from django.utils import timezone
from django.utils.safestring import mark_safe

from experiments.admin_utils import get_result_context
from experiments.models import (
    Experiment,
    ExperimentAlternative,
)
from experiments import conf
from django.conf.urls import url
from experiments.utils import participant
from experiments.conditional.admin import AdminConditionalInline


class ExperimentAlternativeInline(admin.TabularInline):
    model = ExperimentAlternative
    min_num = 1
    extra = 0


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'state', 'auto_enroll')
    list_filter = ('state', 'start_date', 'end_date', 'auto_enroll')
    ordering = ('-start_date',)
    search_fields = ('=name',)
    actions = None
    readonly_fields = ('start_date', 'end_date', 'state', 'auto_enroll',)
    inlines = (ExperimentAlternativeInline, AdminConditionalInline,)

    def get_fieldsets(self, request, obj=None):
        """
        Slightly different fields are shown for Add and Change:
         - default_alternative can only be changed
         - name can only be set on Add
        """
        main_fields = (
            'description', 'start_date', 'end_date', 'auto_enroll', 'state',)

        if obj:
            main_fields += ('default_alternative',)
        else:
            main_fields = ('name',) + main_fields

        return (
            (None, {
                'fields': main_fields,
            }),
            ('Alternatives', {
                'classes': ('js-alternatives',),
                'fields': (),
                'description': mark_safe(
                    '"<strong>control</strong>" alternative will be'
                    ' created if missing.<br />'
                    '<strong>Weights</strong> can all be empty (equal'
                    ' distribution of traffic). <br />'
                    'If only some weights are empty, they will be set to'
                    ' average weight of other alternatives.'),
            }),
            ('Relevant Goals', {
                'classes': ('collapse', 'hidden-relevant-goals'),
                'fields': ('relevant_chi2_goals', 'relevant_mwu_goals'),
            }),
        )

    def get_inline_instances(self, request, obj=None):
        inlines = list(super(ExperimentAdmin, self).get_inline_instances(
            request, obj))
        if obj and obj.pk and not obj.auto_enroll:
            inlines = []
        return inlines

    def get_form(self, request, obj=None, **kwargs):
        """
        Add the default alternative dropdown with appropriate choices
        """

        class NewExperimentModelForm(forms.ModelForm):
            def __init__(self, *args, **kwargs):
                super(NewExperimentModelForm, self).__init__(*args, **kwargs)
                self.instance.auto_enroll = True

        if obj:
            if obj.alternatives:
                choices = [(alternative, alternative) for alternative in obj.alternatives.keys()]
            else:
                choices = [(conf.CONTROL_GROUP, conf.CONTROL_GROUP)]

            class ExperimentModelForm(forms.ModelForm):
                default_alternative = forms.ChoiceField(
                    choices=sorted(choices),
                    initial=obj.default_alternative,
                    required=False,
                )

            kwargs['form'] = ExperimentModelForm
        else:
            kwargs['form'] = NewExperimentModelForm
        return super(ExperimentAdmin, self).get_form(request, obj=obj, **kwargs)

    def save_model(self, request, obj, form, change):
        if change:
            obj.set_default_alternative(form.cleaned_data['default_alternative'])
        obj.save()

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        self._update_obj_alternatives_dict(form.instance)

    def _update_obj_alternatives_dict(self, obj):
        """
        Read ExperimentAlternative inlines and update obj.alternatives.
        Only operated if obj.auto_enroll == True
        """

        if not obj.auto_enroll:
            return

        def update_obj():
            Experiment.objects.filter(pk=obj.pk).update(
                alternatives=obj.alternatives)

        default = obj.default_alternative
        alternatives = obj.experimentalternative_set.all()
        if not alternatives.filter(name=conf.CONTROL_GROUP).exists():
            ExperimentAlternative.objects.create(
                experiment=obj,
                name=conf.CONTROL_GROUP,
            )
        weightless = alternatives.filter(weight__isnull=True)
        weighted = alternatives.exclude(weight__isnull=True)

        if not alternatives.exists():
            # short-circuit the calculations below
            obj.alternatives = {}
            update_obj()
            return

        # fill out missing weight values
        if alternatives.count() == weightless.count():
            # no alternative has specified weight, don't fill anything
            pass
        else:
            # set missing weights to be average of existing values
            total_weight = sum(weighted.values_list('weight', flat=True))
            equality_weight = total_weight / weighted.count()
            weightless.update(weight=equality_weight)

        # update obj.alternatives dict
        obj.alternatives = {
            a.name: a.to_dict()
            for a in alternatives
        }
        if default not in obj.alternatives:
            default = conf.CONTROL_GROUP
        obj.alternatives[default]['default'] = True
        update_obj()

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
