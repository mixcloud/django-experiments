from __future__ import absolute_import

from datetime import timedelta

from django.test import TestCase
from django.test.client import RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore as DatabaseSession
from django.utils import timezone

from experiments.experiment_counters import ExperimentCounter
from experiments.models import Experiment, ENABLED_STATE
from experiments.conf import CONTROL_GROUP, VISIT_PRESENT_COUNT_GOAL, VISIT_NOT_PRESENT_COUNT_GOAL
from experiments.utils import participant

from mock import patch

request_factory = RequestFactory()

TEST_ALTERNATIVE = 'blue'
TEST_GOAL = 'buy'
EXPERIMENT_NAME = 'backgroundcolor'


class WebUserTests(object):
    def setUp(self):
        self.experiment = Experiment(name=EXPERIMENT_NAME, state=ENABLED_STATE)
        self.experiment.save()
        self.request = request_factory.get('/')
        self.request.session = DatabaseSession()
        self.experiment_counter = ExperimentCounter()

    def tearDown(self):
        self.experiment_counter.delete(self.experiment)

    def test_enrollment_initially_control(self):
        experiment_user = participant(self.request)
        self.assertEqual(experiment_user.get_alternative(EXPERIMENT_NAME), 'control', "Default Enrollment wasn't control")

    def test_user_enrolls(self):
        experiment_user = participant(self.request)
        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)
        self.assertEqual(experiment_user.get_alternative(EXPERIMENT_NAME), TEST_ALTERNATIVE, "Wrong Alternative Set")

    def test_record_goal_increments_counts(self):
        experiment_user = participant(self.request)
        experiment_user.confirm_human()
        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)

        self.assertEqual(self.experiment_counter.goal_count(self.experiment, TEST_ALTERNATIVE, TEST_GOAL), 0)
        experiment_user.goal(TEST_GOAL)
        self.assertEqual(self.experiment_counter.goal_count(self.experiment, TEST_ALTERNATIVE, TEST_GOAL), 1, "Did not increment Goal count")

    def test_can_record_goal_multiple_times(self):
        experiment_user = participant(self.request)
        experiment_user.confirm_human()
        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)

        experiment_user.goal(TEST_GOAL)
        experiment_user.goal(TEST_GOAL)
        experiment_user.goal(TEST_GOAL)
        self.assertEqual(self.experiment_counter.goal_count(self.experiment, TEST_ALTERNATIVE, TEST_GOAL), 1, "Did not increment goal count correctly")
        self.assertEqual(self.experiment_counter.goal_distribution(self.experiment, TEST_ALTERNATIVE, TEST_GOAL), {3: 1}, "Incorrect goal count distribution")

    def test_counts_increment_immediately_once_confirmed_human(self):
        experiment_user = participant(self.request)
        experiment_user.confirm_human()

        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)
        self.assertEqual(self.experiment_counter.participant_count(self.experiment, TEST_ALTERNATIVE), 1, "Did not count participant after confirm human")

    def test_visit_increases_goal(self):
        thetime = timezone.now()
        with patch('experiments.utils.now', return_value=thetime):
            experiment_user = participant(self.request)
            experiment_user.confirm_human()
            experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)

            experiment_user.visit()
            # we have two different goals, VISIT_NOT_PRESENT_COUNT_GOAL and VISIT_PRESENT_COUNT_GOAL. Present will avoid firing on the first time we set last_seen as this is assumed that the user is
            # on the page and therefore it would automatically trigger and be valueless. This should be used for experiments when we enroll the user as part of the pageview
            # Alternatively we can use the NOT_PRESENT GOAL which will increment on the first pageview, this is mainly useful for notification actions when the users isn't initially present.
            self.assertEqual(self.experiment_counter.goal_distribution(self.experiment, TEST_ALTERNATIVE, VISIT_NOT_PRESENT_COUNT_GOAL), {1: 1}, "Not Present Visit was not correctly counted")
            self.assertEqual(self.experiment_counter.goal_distribution(self.experiment, TEST_ALTERNATIVE, VISIT_PRESENT_COUNT_GOAL), {}, "Present Visit was not correctly counted")

        with patch('experiments.utils.now', return_value=thetime + timedelta(hours=7)):
            experiment_user.visit()
            self.assertEqual(self.experiment_counter.goal_distribution(self.experiment, TEST_ALTERNATIVE, VISIT_NOT_PRESENT_COUNT_GOAL), {2: 1}, "No Present Visit was not correctly counted")
            self.assertEqual(self.experiment_counter.goal_distribution(self.experiment, TEST_ALTERNATIVE, VISIT_PRESENT_COUNT_GOAL), {1: 1}, "Present Visit was not correctly counted")

    def test_visit_twice_increases_once(self):
        experiment_user = participant(self.request)
        experiment_user.confirm_human()
        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)

        experiment_user.visit()
        experiment_user.visit()

        self.assertEqual(self.experiment_counter.goal_distribution(self.experiment, TEST_ALTERNATIVE, VISIT_NOT_PRESENT_COUNT_GOAL), {1: 1}, "Visit was not correctly counted")


class WebUserAnonymousTestCase(WebUserTests, TestCase):
    def setUp(self):
        super(WebUserAnonymousTestCase, self).setUp()
        self.request.user = AnonymousUser()

    def test_confirm_human_increments_participant_count(self):
        experiment_user = participant(self.request)
        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)
        experiment_user.goal(TEST_GOAL)

        self.assertEqual(self.experiment_counter.participant_count(self.experiment, TEST_ALTERNATIVE), 0, "Counted participant before confirmed human")
        experiment_user.confirm_human()
        self.assertEqual(self.experiment_counter.participant_count(self.experiment, TEST_ALTERNATIVE), 1, "Did not count participant after confirm human")

    def test_confirm_human_increments_goal_count(self):
        experiment_user = participant(self.request)
        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)
        experiment_user.goal(TEST_GOAL)

        self.assertEqual(self.experiment_counter.goal_count(self.experiment, TEST_ALTERNATIVE, TEST_GOAL), 0, "Counted goal before confirmed human")
        experiment_user.confirm_human()
        self.assertEqual(self.experiment_counter.goal_count(self.experiment, TEST_ALTERNATIVE, TEST_GOAL), 1, "Did not count goal after confirm human")


class WebUserAuthenticatedTestCase(WebUserTests, TestCase):
    def setUp(self):
        super(WebUserAuthenticatedTestCase, self).setUp()
        User = get_user_model()
        self.request.user = User(username='brian')
        self.request.user.save()

class BotTests(object):
    def setUp(self):
        self.experiment = Experiment(name='backgroundcolor', state=ENABLED_STATE)
        self.experiment.save()
        self.experiment_counter = ExperimentCounter()

    def test_user_does_not_enroll(self):
        self.experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)
        self.assertEqual(self.experiment_counter.participant_count(self.experiment, TEST_ALTERNATIVE), 0, "Bot counted towards results")

    def test_user_does_not_fire_goals(self):
        self.experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)
        self.experiment_user.goal(TEST_GOAL)
        self.assertEqual(self.experiment_counter.participant_count(self.experiment, TEST_ALTERNATIVE), 0, "Bot counted towards results")

    def test_bot_in_control_group(self):
        self.experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)
        self.assertEqual(self.experiment_user.get_alternative(EXPERIMENT_NAME), 'control', "Bot enrolled in a group")
        self.assertEqual(self.experiment_user.is_enrolled(self.experiment.name, TEST_ALTERNATIVE), False, "Bot in test alternative")
        self.assertEqual(self.experiment_user.is_enrolled(self.experiment.name, CONTROL_GROUP), True, "Bot not in control group")

    def tearDown(self):
        self.experiment_counter.delete(self.experiment)

class LoggedOutBotTestCase(BotTests, TestCase):
    def setUp(self):
        super(LoggedOutBotTestCase, self).setUp()
        self.request = request_factory.get('/', HTTP_USER_AGENT='GoogleBot/2.1')
        self.experiment_user = participant(self.request)


class LoggedInBotTestCase(BotTests, TestCase):
    def setUp(self):
        super(LoggedInBotTestCase, self).setUp()
        User = get_user_model()
        self.user = User(username='brian')
        self.user.is_confirmed_human = False
        self.user.save()

        self.experiment_user = participant(user=self.user)
