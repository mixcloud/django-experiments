# coding=utf-8
from django.conf.urls import url, include

from .views import APIVersionsView
from .v1 import urls as v1_users

app_name = 'api'
urlpatterns = [
    url(r'^$', APIVersionsView.as_view(), name='versions'),
    url(r'^v1/', include(v1_users, namespace='v1')),
]
