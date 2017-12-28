# coding=utf-8
from django.conf.urls import url
from django.http.response import HttpResponsePermanentRedirect
from rest_framework.reverse import reverse_lazy

from .views import (
    APIRootView,
    ExperimentsListView,
    ExperimentView,
    RemoteExperimentStateView,
    RemoteExperimentView,
)


app_name = 'v1'
urlpatterns = [

    url(r'^$',
        APIRootView.as_view(),
        name='root'),

    url(r'^experiments/$',
        lambda r: HttpResponsePermanentRedirect(
            reverse_lazy('experiments:api:v1:experiments'))
        ),

    url(r'^experiment/$',
        ExperimentsListView.as_view(),
        name='experiments'),

    url(r'^experiment/(?P<name>[-\w]+)/$',
        ExperimentView.as_view(),
        name='experiment'),

    url(r'^remote_experiment/$',
        RemoteExperimentView.as_view(),
        name='remote_experiments'),

    url(r'^remote_experiment/(?P<pk>[0-9]+)/state/$',
        RemoteExperimentStateView.as_view(),
        name='remote_experiment_state'),


]
