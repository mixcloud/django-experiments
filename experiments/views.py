# coding=utf-8
from functools import wraps

from django.conf.urls import url
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.views.generic.base import ContextMixin, View
from experiments import conf
from experiments.models import Experiment
from experiments.utils import participant


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
@require_POST
def confirm_human(request):
    if conf.CONFIRM_HUMAN:
        experiment_user = participant(request)
        experiment_user.confirm_human()
    return HttpResponse(status=204)


@never_cache
def record_experiment_goal(request, goal_name, cache_buster=None):
    participant(request).goal(goal_name)
    return HttpResponse(TRANSPARENT_1X1_PNG, content_type="image/png")


def change_alternative(request, experiment_name, alternative_name):
    experiment = get_object_or_404(Experiment, name=experiment_name)
    if alternative_name not in experiment.alternatives.keys():
        return HttpResponseBadRequest()

    participant(request).set_alternative(experiment_name, alternative_name)
    return HttpResponse('OK')


def decorate(decorators, patterns_rslt):
    '''
    Used to require 1..n decorators in any view returned by a url tree
    Usage:
      urlpatterns = required(func,patterns(...))
      urlpatterns = required((func,func,func),patterns(...))
    Note:
      Use functools.partial to pass keyword params to the required
      decorators. If you need to pass args you will have to write a
      wrapper function.
    Example:
      from functools import partial
      urlpatterns = required(
          partial(login_required,login_url='/accounts/login/'),
          patterns(...)
      )
    '''
    if not hasattr(decorators,'__iter__'):
        decorators = (decorators,)

    return [
        _wrap_instance__resolve(decorators, instance)
        for instance in patterns_rslt
    ]

def _wrap_instance__resolve(wrapping_functions, instance):
    if not hasattr(instance, 'resolve'):
        return instance
    
    resolve = getattr(instance, 'resolve')
    def _wrap_func_in_returned_resolver_match(*args,**kwargs):
        rslt = resolve(*args,**kwargs)
        if not hasattr(rslt, 'func'):
            return rslt
        
        f = getattr(rslt, 'func')
        for _f in reversed(wrapping_functions):
            # @decorate the function from inner to outter
            f = _f(f)

        setattr(rslt, 'func', f)
        return rslt

    setattr(instance,'resolve',_wrap_func_in_returned_resolver_match)
    return instance
