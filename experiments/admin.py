from django.contrib import admin

from django import forms
from experiments.models import Experiment, Enrollment

class ExperimentAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'state')
    list_filter = ('name', 'start_date', 'state')
    search_fields = ('name', )

class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'experiment', 'alternative')
    readonly_fields = ('user', 'experiment',)
    list_filter = ('experiment',)
    search_fields = ('user',)
    raw_id_fields = ('user',)

    def get_form(self, request, obj=None, **kwargs):
        form = super(EnrollmentAdmin, self).get_form(request, obj, **kwargs)
        alternatives = obj.experiment.alternatives.keys()
        form.base_fields['alternative'].widget = forms.Select(choices=zip(alternatives, alternatives))
        return form

admin.site.register(Experiment, ExperimentAdmin)
admin.site.register(Enrollment, EnrollmentAdmin)
