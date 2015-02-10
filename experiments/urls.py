from django.conf.urls import patterns, url

urlpatterns = patterns('experiments.views',
    url(r'^goal/(?P<goal_name>[^/]+)/(?P<cache_buster>[^/]+)?$', 'record_experiment_goal', name="experiment_goal"),
    url(r'^confirm_human/$', 'confirm_human', name="experiment_confirm_human"),
    url(r'^change_alternative/(?P<experiment_name>[a-zA-Z0-9-_]+)/(?P<alternative_name>[a-zA-Z0-9-_]+)/$', 'change_alternative', name="experiment_change_alternative"),
)
