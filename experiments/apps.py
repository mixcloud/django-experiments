from django.apps import AppConfig

from experiments.utils import _record_goal as record_goal

from django.contrib.auth.signals import user_logged_in
from experiments.signal_handlers import transfer_enrollments_to_user


class ExperimentsConfig(AppConfig):
    def ready(self):
        user_logged_in.connect(transfer_enrollments_to_user, dispatch_uid="experiments_user_logged_in")

