from django.db.models.signals import post_delete
from experiments.models import Experiment

from experiments.signals import redis_counter_tidy

post_delete.connect(redis_counter_tidy, sender=Experiment, dispatch_uid="redis_counter_reset")