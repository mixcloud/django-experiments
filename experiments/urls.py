from django.conf.urls import url
from experiments import views

urlpatterns = [
    url(r'^goal/(?P<goal_name>[^/]+)/(?P<cache_buster>[^/]+)?$', views.record_experiment_goal, name="experiment_goal"),
    url(r'^confirm_human/$', views.confirm_human, name="experiment_confirm_human"),
    url(r'^change_alternative/(?P<experiment_name>[a-zA-Z0-9-_]+)/(?P<alternative_name>[a-zA-Z0-9-_]+)/$', views.change_alternative, name="experiment_change_alternative"),
]
