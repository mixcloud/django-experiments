from django.contrib import admin

from experiments.models import Experiment, Enrollment


class ExperimentAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'state')
    list_filter = ('name', 'start_date', 'state')
    search_fields = ('name', )

admin.site.register(Enrollment)
admin.site.register(Experiment, ExperimentAdmin)
