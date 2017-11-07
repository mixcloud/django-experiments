# coding=utf-8
"""
Contains helpers to dynamically add `ExperimentalMixin` to `View` classes.
This can be useful for projects that have a large number of views.

Usage A: url():
    urls.py:

        # instead of from django.conf.urls import url, do this:
        from experiments.conditional import url

        urlpatterns = [
            url(r'^$', MyView.as_view(), name='my_view'),
            ...
        ]

    note:
      `url()` helper is _not_ recursive, i.e. it will have no effect on
      include calls like `url(r'^myapp/', include('myapp.urls'))`.
      It will also have no effect on function (i.e. non-class-based) views.


Usage B: experimentize() with regular views:

    urls.py:

        # standard import:
        django.conf.urls import url

        urlpatterns = [
            url(r'^$', experimentize(MyView.as_view()), name='my_view'),
            # or:
            url(r'^$', experimentize(MyView).as_view(), name='my_view'),
            ...
            url(r'^$', MyNoExperView.as_view(), name='my_no_experiment_view'),
        ]


Usage C: with Django Rest Framework's Routers:

    urls.py:

        router = DefaultRouter()
        router.register(
            r'', experimentize(RestHookViewSet), base_name='resthook'),
            ...
        )
        urlpatterns = router.urls

"""
from __future__ import absolute_import

from django import VERSION as DJANGO_VERSION
from django.conf.urls import url as django_url
from django.core.exceptions import ImproperlyConfigured
from django.views.generic import View

from .views import ExperimentsMixin

__all__ = [
    'experimentize',
    'url',
]


def experimentize(view):
    """
    Dynamically adds a mixin to the provided view instance.

    Should be used with Django class based views and views from
    Django Rest Framework.
    Other view (e.g. functions) are left unaffected.

    This function is idempotent (can be safely applied multiple times).
    """
    if DJANGO_VERSION < (1, 9):
        raise ImproperlyConfigured(
            'experiments.conditional.urls is supported on Django >= 1.9. '
            'Consider adding ExperimentsMixin to your views explicitly.')
    if isinstance(view, type) and issubclass(view, View):
        view_class = view
    else:
        view_class = getattr(view, 'view_class', getattr(view, 'cls', None))
    if view_class and not issubclass(view_class, ExperimentsMixin):
        view_class.__bases__ = (ExperimentsMixin,) + view_class.__bases__
    return view


def url(regex, view, kwargs=None, name=None):
    """
    Drop-in replacement for django.conf.urls.url.
    Calls experimentize() on the view.
    Then passes the call to django.conf.urls.url.
    """
    view = experimentize(view)
    return django_url(regex, view, kwargs, name)
