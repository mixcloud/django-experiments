from django.test import TestCase
from django.utils.unittest import TestSuite
from django.contrib.sessions.backends.db import SessionStore as DatabaseSession

from experiments.experiment_counters import ExperimentCounter
from experiments.utils import DummyUser, SessionUser, AuthenticatedUser
from experiments.models import Experiment, ENABLED_STATE

from django.contrib.auth import get_user_model

TEST_ALTERNATIVE = 'blue'
EXPERIMENT_NAME = 'backgroundcolor'


class WebUserIncorporateTestCase(object):
    def __init__(self, *args, **kwargs):
        super(WebUserIncorporateTestCase, self).__init__(*args, **kwargs)
        self.experiment_counter = ExperimentCounter()

    def test_can_incorporate(self):
        self.incorporating.incorporate(self.incorporated)

    def test_incorporates_enrollment_from_other(self):
        if not self._has_data():
            return

        try:
            experiment = Experiment.objects.create(name=EXPERIMENT_NAME, state=ENABLED_STATE)
            self.incorporated.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)
            self.incorporating.incorporate(self.incorporated)
            self.assertEqual(self.incorporating.get_alternative(EXPERIMENT_NAME), TEST_ALTERNATIVE)
        finally:
            self.experiment_counter.delete(experiment)

    def _has_data(self):
        return not isinstance(self.incorporated, DummyUser) and not isinstance(self.incorporating, DummyUser)


def dummy(incorporating):
    return DummyUser()


def anonymous(incorporating):
    return SessionUser(session=DatabaseSession())


def authenticated(incorporating):
    User = get_user_model()
    return AuthenticatedUser(user=User.objects.create(username=['incorporating_user', 'incorporated_user'][incorporating]))

user_factories = (dummy, anonymous, authenticated)


def load_tests(loader, standard_tests, _):
    suite = TestSuite()
    suite.addTests(standard_tests)

    for incorporating in user_factories:
        for incorporated in user_factories:
            test_case = build_test_case(incorporating, incorporated)
            tests = loader.loadTestsFromTestCase(test_case)
            suite.addTests(tests)
    return suite


def build_test_case(incorporating, incorporated):
    class InstantiatedTestCase(WebUserIncorporateTestCase, TestCase):

        def setUp(self):
            super(InstantiatedTestCase, self).setUp()
            self.incorporating = incorporating(True)
            self.incorporated = incorporated(False)
    InstantiatedTestCase.__name__ = "WebUserIncorporateTestCase_into_%s_from_%s" % (incorporating.__name__, incorporated.__name__)
    return InstantiatedTestCase
