from django.db.models.signals import post_delete
from django.contrib.auth.signals import user_logged_in
from experiments.models import Experiment

from experiments.signals import redis_counter_tidy
from experiments.utils import sync_experiments

post_delete.connect(redis_counter_tidy, sender=Experiment, dispatch_uid="redis_counter_reset")
user_logged_in.connect(sync_experiments)