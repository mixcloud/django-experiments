import django.dispatch

experiment_added = django.dispatch.Signal(providing_args=["request", "experiment"])

experiment_deleted = django.dispatch.Signal(providing_args=["request", "experiment"])

experiment_updated = django.dispatch.Signal(providing_args=["request", "experiment"])

experiment_state_updated = django.dispatch.Signal(providing_args=["request", "experiment", "state"])

experiment_user_added = django.dispatch.Signal(providing_args=["request", "experiment", "user", "alternative"])

experiment_incr_participant = django.dispatch.Signal(providing_args=["request", "experiment", "alternative", "participants", "user"])

goal_hit = django.dispatch.Signal(providing_args=["request", "experiment", "alternative", "goal", "hits", "user"])

user_confirmed_human = django.dispatch.Signal(providing_args=["request", "user"])

# Reset redis counters when deleting an experiment
from counters import counter_reset_pattern
def redis_counter_tidy(instance, **kwargs):
    counter_reset_pattern(instance.name + "*")

#: Other, standard django signal handlers of interest include:
#:     pre_save
#:     post_save
#:     pre_delete
#:     post_delete
#: For usage and examples, see https://docs.djangoproject.com/en/dev/topics/signals/

#: Test/Example Callbacks

#: def experiment_added_callback(sender, request, **kwargs):
#: 	print kwargs
#: experiment_added.connect(experiment_added_callback)

#: def experiment_deleted_callback(sender, request, **kwargs):
#: 	print kwargs
#: experiment_deleted.connect(experiment_deleted_callback)

#: def experiment_updated_callback(sender, request, **kwargs):
#: 	print kwargs
#: experiment_updated.connect(experiment_updated_callback)

#: def experiment_state_updated_callback(sender, request, **kwargs):
#: 	print kwargs
#: experiment_state_updated.connect(experiment_state_updated_callback)

#: def experiment_user_added_callback(sender, request, **kwargs):
#: 	print kwargs
#: experiment_user_added.connect(experiment_user_added_callback)

#: experiment_incr_participant_callback(sender, request, **kwargs):
#: 	print kwargs
#: experiment_incr_participant.connect(experiment_incr_participant_callback)

#: def goal_hit_callback(sender, request, **kwargs):
#: 	print kwargs
#: goal_hit.connect(goal_hit_callback)

#: def user_confirmed_human_callback(sender, request, **kwargs):
#: 	print kwargs
#: user_confirmed_human.connect(user_confirmed_human_callback)