from __future__ import absolute_import

from django.test import TestCase
from django.test.client import RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.db import SessionStore as DatabaseSession

from experiments.models import Experiment, ENABLED_STATE
from experiments.conf import CONTROL_GROUP, VISIT_COUNT_GOAL
from experiments.utils import participant

User = get_user_model()
request_factory = RequestFactory()

TEST_ALTERNATIVE = 'blue'
TEST_GOAL = 'buy'
EXPERIMENT_NAME='backgroundcolor'

class WebUserTests:
    def setUp(self):
        self.experiment = Experiment(name=EXPERIMENT_NAME, state=ENABLED_STATE)
        self.experiment.save()
        self.request = request_factory.get('/')
        self.request.session = DatabaseSession()

    def tearDown(self):
        self.experiment.delete()

    def confirm_human(self, experiment_user):
        pass

    def participants(self, alternative):
        return self.experiment.participant_count(alternative)

    def enrollment_initially_none(self,):
        experiment_user = participant(self.request)
        self.assertEqual(experiment_user.get_alternative(EXPERIMENT_NAME), None)

    def test_user_enrolls(self):
        experiment_user = participant(self.request)
        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)
        self.assertEqual(experiment_user.get_alternative(EXPERIMENT_NAME), TEST_ALTERNATIVE)

    def test_record_goal_increments_counts(self):
        experiment_user = participant(self.request)
        self.confirm_human(experiment_user)
        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)

        self.assertEqual(self.experiment.goal_count(TEST_ALTERNATIVE, TEST_GOAL), 0)
        experiment_user.goal(TEST_GOAL)
        self.assertEqual(self.experiment.goal_count(TEST_ALTERNATIVE, TEST_GOAL), 1)

    def test_can_record_goal_multiple_times(self):
        experiment_user = participant(self.request)
        self.confirm_human(experiment_user)
        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)

        experiment_user.goal(TEST_GOAL)
        experiment_user.goal(TEST_GOAL)
        experiment_user.goal(TEST_GOAL)
        self.assertEqual(self.experiment.goal_count(TEST_ALTERNATIVE, TEST_GOAL), 1)

    def test_counts_increment_immediately_once_confirmed_human(self):
        experiment_user = participant(self.request)
        self.confirm_human(experiment_user)

        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)
        self.assertEqual(self.participants(TEST_ALTERNATIVE), 1, "Did not count participant after confirm human")

    def test_visit_increases_goal(self):
        experiment_user = participant(self.request)
        self.confirm_human(experiment_user)
        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)

        experiment_user.visit()

        self.assertEqual(self.experiment.goal_distribution(TEST_ALTERNATIVE, VISIT_COUNT_GOAL), {1: 1})

    def test_visit_twice_increases_once(self):
        experiment_user = participant(self.request)
        self.confirm_human(experiment_user)
        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)

        experiment_user.visit()
        experiment_user.visit()

        self.assertEqual(self.experiment.goal_distribution(TEST_ALTERNATIVE, VISIT_COUNT_GOAL), {1: 1})


class WebUserAnonymousTestCase(WebUserTests, TestCase):
    def setUp(self):
        super(WebUserAnonymousTestCase, self).setUp()
        self.request.user = AnonymousUser()

    def confirm_human(self, experiment_user):
        experiment_user.confirm_human()

    def test_confirm_human_increments_counts(self):
        experiment_user = participant(self.request)
        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)
        experiment_user.goal(TEST_GOAL)

        self.assertEqual(self.participants(TEST_ALTERNATIVE), 0, "Counted participant before confirmed human")
        self.assertEqual(self.experiment.goal_count(TEST_ALTERNATIVE, TEST_GOAL), 0, "Counted goal before confirmed human")
        experiment_user.confirm_human()
        self.assertEqual(self.participants(TEST_ALTERNATIVE), 1, "Did not count participant after confirm human")
        self.assertEqual(self.experiment.goal_count(TEST_ALTERNATIVE, TEST_GOAL), 1, "Did not count goal after confirm human")


class WebUserAuthenticatedTestCase(WebUserTests, TestCase):
    def setUp(self):
        super(WebUserAuthenticatedTestCase, self).setUp()
        self.request.user = User(username='brian')
        self.request.user.save()


class BotTestCase(TestCase):
    def setUp(self):
        self.experiment = Experiment(name='backgroundcolor', state=ENABLED_STATE)
        self.experiment.save()
        self.request = request_factory.get('/', HTTP_USER_AGENT='GoogleBot/2.1')

    def test_user_does_not_enroll(self):
        experiment_user = participant(self.request)
        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)
        self.assertEqual(self.experiment.participant_count(TEST_ALTERNATIVE), 0, "Bot counted towards results")

    def test_bot_in_control_group(self):
        experiment_user = participant(self.request)
        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)
        self.assertEqual(experiment_user.get_alternative(EXPERIMENT_NAME), 'control', "Bot enrolled in a group")
        self.assertEqual(experiment_user.is_enrolled(self.experiment.name, TEST_ALTERNATIVE, self.request), False, "Bot in test alternative")
        self.assertEqual(experiment_user.is_enrolled(self.experiment.name, CONTROL_GROUP, self.request), True, "Bot not in control group")

    def tearDown(self):
        self.experiment.delete()

