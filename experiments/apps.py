from django.apps import AppConfig


class ExperimentsConfig(AppConfig):
    name = 'experiments'
    label = 'experiments'

    def ready(self):
        from django.contrib.auth.signals import user_logged_in
        from experiments.signal_handlers import transfer_enrollments_to_user

        user_logged_in.connect(transfer_enrollments_to_user, dispatch_uid="experiments_user_logged_in")

