from django.conf.urls.defaults import *

urlpatterns = patterns('experiments.views',
    url(r'^goal/(?P<goal_name>.*)$', 'record_experiment_goal', name="experiment_goal"),
    url(r'^confirm_human/$', 'confirm_human', name="experiment_confirm_human"),
    url(r'^change_alternative/(?P<experiment_name>[a-zA-Z0-9-_]+)/(?P<alternative_name>[a-zA-Z0-9-_]+)/$', 'change_alternative', name="experiment_change_alternative"),
)
