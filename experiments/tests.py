from __future__ import absolute_import

from django.utils.unittest import TestCase
from django.test.client import RequestFactory
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.sessions.backends.db import SessionStore as DatabaseSession

from experiments import stats, counters
from experiments.utils import create_user
from experiments.models import Experiment, ENABLED_STATE, CONTROL_GROUP

request_factory = RequestFactory()
TEST_KEY = 'CounterTestCase'
TEST_ALTERNATIVE = 'blue'
TEST_GOAL = 'buy'

class StatsTestCase(TestCase):
    def test_flatten(self):
        self.assertEqual(
            list(stats.flatten([1,[2,[3]],4,5])),
            [1,2,3,4,5]
            )


class CounterTestCase(TestCase):
    def setUp(self):
        counters.reset(TEST_KEY)
        self.assertEqual(counters.get(TEST_KEY), 0)

    def tearDown(self):
        counters.reset(TEST_KEY)

    def test_add_item(self):
        counters.increment(TEST_KEY, 'fred')
        self.assertEqual(counters.get(TEST_KEY), 1)

    def test_add_multiple_items(self):
        counters.increment(TEST_KEY, 'fred')
        counters.increment(TEST_KEY, 'barney')
        counters.increment(TEST_KEY, 'george')
        self.assertEqual(counters.get(TEST_KEY), 3)

    def test_add_duplicate_item(self):
        counters.increment(TEST_KEY, 'fred')
        counters.increment(TEST_KEY, 'fred')
        counters.increment(TEST_KEY, 'fred')
        self.assertEqual(counters.get(TEST_KEY), 1)

    def test_delete_key(self):
        counters.increment(TEST_KEY, 'fred')
        counters.reset(TEST_KEY)
        self.assertEqual(counters.get(TEST_KEY), 0)


class WebUserTests:
    def setUp(self):
        self.experiment = Experiment(name='backgroundcolor', state=ENABLED_STATE)
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
        experiment_user = create_user(self.request)
        self.assertEqual(experiment_user.get_enrollment(self.experiment), None)

    def test_user_enrolls(self):
        experiment_user = create_user(self.request)
        experiment_user.set_enrollment(self.experiment, TEST_ALTERNATIVE)
        self.assertEqual(experiment_user.get_enrollment(self.experiment), TEST_ALTERNATIVE)

    def test_record_goal_increments_counts(self):
        experiment_user = create_user(self.request)
        self.confirm_human(experiment_user)
        experiment_user.set_enrollment(self.experiment, TEST_ALTERNATIVE)

        self.assertEqual(self.experiment.goal_count(TEST_ALTERNATIVE, TEST_GOAL), 0)
        experiment_user.record_goal(TEST_GOAL)
        self.assertEqual(self.experiment.goal_count(TEST_ALTERNATIVE, TEST_GOAL), 1)

    def test_can_record_goal_multiple_times(self):
        experiment_user = create_user(self.request)
        self.confirm_human(experiment_user)
        experiment_user.set_enrollment(self.experiment, TEST_ALTERNATIVE)

        experiment_user.record_goal(TEST_GOAL)
        experiment_user.record_goal(TEST_GOAL)
        experiment_user.record_goal(TEST_GOAL)
        self.assertEqual(self.experiment.goal_count(TEST_ALTERNATIVE, TEST_GOAL), 1)

    def test_counts_increment_immediately_once_confirmed_human(self):
        experiment_user = create_user(self.request)
        self.confirm_human(experiment_user)

        experiment_user.set_enrollment(self.experiment, TEST_ALTERNATIVE)
        self.assertEqual(self.participants(TEST_ALTERNATIVE), 1, "Did not count participant after confirm human")


class WebUserAnonymousTestCase(WebUserTests, TestCase):
    def setUp(self):
        super(WebUserAnonymousTestCase, self).setUp()
        self.request.user = AnonymousUser()

    def confirm_human(self, experiment_user):
        experiment_user.confirm_human()

    def test_confirm_human_increments_counts(self):
        experiment_user = create_user(self.request)
        experiment_user.set_enrollment(self.experiment, TEST_ALTERNATIVE)

        self.assertEqual(self.participants(TEST_ALTERNATIVE), 0, "Counted participant before confirmed human")
        experiment_user.confirm_human()
        self.assertEqual(self.participants(TEST_ALTERNATIVE), 1, "Did not count participant after confirm human")


class WebUserAuthenticatedTestCase(WebUserTests, TestCase):
    def setUp(self):
        super(WebUserAuthenticatedTestCase, self).setUp()
        self.request.user = User(username='brian')
        self.request.user.save()

    def tearDown(self):
        self.request.user.delete()
        super(WebUserAuthenticatedTestCase, self).tearDown()


class BotTestCase(TestCase):
    def setUp(self):
        self.experiment = Experiment(name='backgroundcolor', state=ENABLED_STATE)
        self.experiment.save()
        self.request = request_factory.get('/', HTTP_USER_AGENT='GoogleBot/2.1')

    def test_user_does_not_enroll(self):
        experiment_user = create_user(self.request)
        experiment_user.set_enrollment(self.experiment, TEST_ALTERNATIVE)
        self.assertEqual(self.experiment.participant_count(TEST_ALTERNATIVE), 0, "Bot counted towards results")

    def test_bot_in_control_group(self):
        experiment_user = create_user(self.request)
        experiment_user.set_enrollment(self.experiment, TEST_ALTERNATIVE)
        self.assertEqual(experiment_user.get_enrollment(self.experiment), CONTROL_GROUP, "Bot alternative is not control")
        self.assertEqual(experiment_user.is_enrolled(self.experiment.name, TEST_ALTERNATIVE, self.request), False, "Bot in test alternative")
        self.assertEqual(experiment_user.is_enrolled(self.experiment.name, CONTROL_GROUP, self.request), True, "Bot not in control group")

    def tearDown(self):
        self.experiment.delete()

