from __future__ import absolute_import

from datetime import timedelta
from django.http import HttpResponse

from django.test import TestCase
from django.test.client import RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore as DatabaseSession
from django.utils import timezone
from experiments import conf

from experiments.experiment_counters import ExperimentCounter
from experiments.middleware import ExperimentsRetentionMiddleware
from experiments.models import Experiment, ENABLED_STATE, Enrollment
from experiments.conf import CONTROL_GROUP, VISIT_PRESENT_COUNT_GOAL, VISIT_NOT_PRESENT_COUNT_GOAL
from experiments.signal_handlers import transfer_enrollments_to_user
from experiments.utils import participant

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

import random

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
        self.assertEqual(self.experiment_counter.goal_distribution(self.experiment, TEST_ALTERNATIVE, VISIT_PRESENT_COUNT_GOAL), {}, "Present Visit was not correctly counted")

    def test_user_force_enrolls(self):
        experiment_user = participant(self.request)
        experiment_user.enroll(EXPERIMENT_NAME, ['control', 'alternative1', 'alternative2'], force_alternative='alternative2')
        self.assertEqual(experiment_user.get_alternative(EXPERIMENT_NAME), 'alternative2')

    def test_user_does_not_force_enroll_to_new_alternative(self):
        alternatives = ['control', 'alternative1', 'alternative2']
        experiment_user = participant(self.request)
        experiment_user.enroll(EXPERIMENT_NAME, alternatives)
        alternative = experiment_user.get_alternative(EXPERIMENT_NAME)
        self.assertIsNotNone(alternative)

        other_alternative = random.choice(list(set(alternatives) - set(alternative)))
        experiment_user.enroll(EXPERIMENT_NAME, alternatives, force_alternative=other_alternative)
        self.assertEqual(alternative, experiment_user.get_alternative(EXPERIMENT_NAME))

    def test_second_force_enroll_does_not_change_alternative(self):
        alternatives = ['control', 'alternative1', 'alternative2']
        experiment_user = participant(self.request)
        experiment_user.enroll(EXPERIMENT_NAME, alternatives, force_alternative='alternative1')
        alternative = experiment_user.get_alternative(EXPERIMENT_NAME)
        self.assertIsNotNone(alternative)

        other_alternative = random.choice(list(set(alternatives) - set(alternative)))
        experiment_user.enroll(EXPERIMENT_NAME, alternatives, force_alternative=other_alternative)
        self.assertEqual(alternative, experiment_user.get_alternative(EXPERIMENT_NAME))


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


class ParticipantCacheTestCase(TestCase):
    def setUp(self):
        self.experiment = Experiment.objects.create(name='test_experiment1', state=ENABLED_STATE)
        self.experiment_counter = ExperimentCounter()

    def tearDown(self):
        self.experiment_counter.delete(self.experiment)

    def test_transfer_enrollments(self):
        User = get_user_model()
        user = User.objects.create(username='test')
        request = request_factory.get('/')
        request.session = DatabaseSession()
        participant(request).enroll('test_experiment1', ['alternative'])
        request.user = user
        transfer_enrollments_to_user(None, request, user)
        # the call to the middleware will set last_seen on the experiment
        # if the participant cache hasn't been wiped appropriately then the
        # session experiment user will be impacted instead of the authenticated
        # experiment user
        ExperimentsRetentionMiddleware().process_response(request, HttpResponse())
        self.assertIsNotNone(Enrollment.objects.all()[0].last_seen)


class ConfirmHumanTestCase(TestCase):
    def setUp(self):
        self.experiment = Experiment.objects.create(name='test_experiment1', state=ENABLED_STATE)
        self.experiment_counter = ExperimentCounter()
        self.experiment_user = participant(session=DatabaseSession())
        self.alternative = self.experiment_user.enroll(self.experiment.name, ['alternative'])
        self.experiment_user.goal('my_goal')

    def tearDown(self):
        self.experiment_counter.delete(self.experiment)

    def test_confirm_human_updates_experiment(self):
        self.assertIn('experiments_goals', self.experiment_user.session)
        self.assertEqual(self.experiment_counter.participant_count(self.experiment, self.alternative), 0)
        self.assertEqual(self.experiment_counter.goal_count(self.experiment, self.alternative, 'my_goal'), 0)
        self.experiment_user.confirm_human()
        self.assertNotIn('experiments_goals', self.experiment_user.session)
        self.assertEqual(self.experiment_counter.participant_count(self.experiment, self.alternative), 1)
        self.assertEqual(self.experiment_counter.goal_count(self.experiment, self.alternative, 'my_goal'), 1)

    def test_confirm_human_called_twice(self):
        """
        Ensuring that counters aren't incremented twice
        """
        self.assertEqual(self.experiment_counter.participant_count(self.experiment, self.alternative), 0)
        self.assertEqual(self.experiment_counter.goal_count(self.experiment, self.alternative, 'my_goal'), 0)
        self.experiment_user.confirm_human()
        self.experiment_user.confirm_human()
        self.assertEqual(self.experiment_counter.participant_count(self.experiment, self.alternative), 1)
        self.assertEqual(self.experiment_counter.goal_count(self.experiment, self.alternative, 'my_goal'), 1)

    def test_confirm_human_sets_session(self):
        self.assertFalse(self.experiment_user.session.get(conf.CONFIRM_HUMAN_SESSION_KEY, False))
        self.experiment_user.confirm_human()
        self.assertTrue(self.experiment_user.session.get(conf.CONFIRM_HUMAN_SESSION_KEY, False))

    def test_session_already_confirmed(self):
        """
        Testing that confirm_human works even if code outside of django-experiments updates the key
        """
        self.experiment_user.session[conf.CONFIRM_HUMAN_SESSION_KEY] = True
        self.experiment_user.confirm_human()
        self.assertEqual(self.experiment_counter.participant_count(self.experiment, self.alternative), 1)
        self.assertEqual(self.experiment_counter.goal_count(self.experiment, self.alternative, 'my_goal'), 1)


class DefaultAlternativeTestCase(TestCase):
    def test_default_alternative(self):
        experiment = Experiment.objects.create(name='test_default')
        self.assertEqual(experiment.default_alternative, conf.CONTROL_GROUP)
        experiment.ensure_alternative_exists('alt1')
        experiment.ensure_alternative_exists('alt2')

        self.assertEqual(conf.CONTROL_GROUP, participant(session=DatabaseSession()).enroll('test_default', ['alt1', 'alt2']))
        experiment.set_default_alternative('alt2')
        experiment.save()
        self.assertEqual('alt2', participant(session=DatabaseSession()).enroll('test_default', ['alt1', 'alt2']))
        experiment.set_default_alternative('alt1')
        experiment.save()
        self.assertEqual('alt1', participant(session=DatabaseSession()).enroll('test_default', ['alt1', 'alt2']))
