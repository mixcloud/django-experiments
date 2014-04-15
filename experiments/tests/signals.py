from django.test import TestCase

try:
    from django.contrib.auth import get_user_model
except ImportError:  # django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()

from experiments.models import Experiment, ENABLED_STATE
from experiments.signals import user_enrolled
from experiments.utils import participant

EXPERIMENT_NAME = 'backgroundcolor'


class WatchSignal(object):
    def __init__(self, signal):
        self.signal = signal
        self.called = False

    def __enter__(self):
        self.signal.connect(self.signal_handler)
        return self

    def __exit__(self, *args):
        self.signal.disconnect(self.signal_handler)

    def signal_handler(self, *args, **kwargs):
        self.called = True


class SignalsTestCase(TestCase):
    def setUp(self):
        self.experiment = Experiment.objects.create(name=EXPERIMENT_NAME, state=ENABLED_STATE)
        self.user = User.objects.create(username='brian')

    def test_sends_enroll_signal(self):
        with WatchSignal(user_enrolled) as signal:
            participant(user=self.user).enroll(EXPERIMENT_NAME, ['red', 'blue'])
            self.assertTrue(signal.called)

    def test_does_not_send_enroll_signal_again(self):
        participant(user=self.user).enroll(EXPERIMENT_NAME, ['red', 'blue'])
        with WatchSignal(user_enrolled) as signal:
            participant(user=self.user).enroll(EXPERIMENT_NAME, ['red', 'blue'])
            self.assertFalse(signal.called)
