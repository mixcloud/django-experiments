from django.contrib.auth.signals import user_logged_in
from experiments.signals import transfer_enrollments_to_user

from experiments.utils import _record_goal as record_goal

user_logged_in.connect(transfer_enrollments_to_user, dispatch_uid="experiments_user_logged_in")
