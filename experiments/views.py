from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.cache import never_cache
from django.shortcuts import get_object_or_404

from experiments.utils import WebUser, record_goal
from experiments.models import Experiment

TRANSPARENT_1X1_PNG = \
("\x89\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52"
 "\x00\x00\x00\x01\x00\x00\x00\x01\x08\x03\x00\x00\x00\x28\xcb\x34"
 "\xbb\x00\x00\x00\x19\x74\x45\x58\x74\x53\x6f\x66\x74\x77\x61\x72"
 "\x65\x00\x41\x64\x6f\x62\x65\x20\x49\x6d\x61\x67\x65\x52\x65\x61"
 "\x64\x79\x71\xc9\x65\x3c\x00\x00\x00\x06\x50\x4c\x54\x45\x00\x00"
 "\x00\x00\x00\x00\xa5\x67\xb9\xcf\x00\x00\x00\x01\x74\x52\x4e\x53"
 "\x00\x40\xe6\xd8\x66\x00\x00\x00\x0c\x49\x44\x41\x54\x78\xda\x62"
 "\x60\x00\x08\x30\x00\x00\x02\x00\x01\x4f\x6d\x59\xe1\x00\x00\x00"
 "\x00\x49\x45\x4e\x44\xae\x42\x60\x82\x00")

@never_cache
def confirm_human(request):
    experiment_user = WebUser(request)
    experiment_user.confirm_human()
    return HttpResponse(status=204)

@never_cache
def record_experiment_goal(request, goal_name):
    record_goal(request, goal_name)
    return HttpResponse(TRANSPARENT_1X1_PNG, mimetype="image/png")

def change_alternative(request, experiment_name, alternative_name):
    experiment = get_object_or_404(Experiment, name=experiment_name)
    if alternative_name not in experiment.alternatives.keys():
        return HttpResponseBadRequest()

    experiment_user = WebUser(request)
    experiment_user.set_enrollment(experiment, alternative_name)
    return HttpResponse('OK')
