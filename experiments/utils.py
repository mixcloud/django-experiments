from django.conf import settings
from django.db import IntegrityError

from experiments.models import Enrollment, CONTROL_GROUP
from experiments.manager import experiment_manager

import re


# Known bots user agents to drop from experiments
BOT_REGEX = re.compile("(Baidu|Gigabot|Googlebot|YandexBot|AhrefsBot|TVersity|libwww-perl|Yeti|lwp-trivial|msnbot|bingbot|facebookexternalhit|Twitterbot|Twitmunin|SiteUptime|TwitterFeed|Slurp|WordPress|ZIBB|ZyBorg)", re.IGNORECASE)


def record_goal(request, goal_name):
    experiment_user = create_user(request)
    experiment_user.record_goal(goal_name)


def create_user(request):
    if BOT_REGEX.search(request.META.get("HTTP_USER_AGENT","")):
        return DummyUser()
    elif request and request.user and request.user.is_authenticated():
        return AuthenticatedUser(request.user)
    elif request and request.session:
        return SessionUser(request.session)
    else:
        return DummyUser()


class WebUser(object):
    """Represents a user (either authenticated or session based) which can take part in experiments"""

    def get_enrollment(self, experiment):
        """Get the name of the alternative this user is enrolled in for the specified experiment
        
        `experiment` is an instance of Experiment. If the user is not currently enrolled returns None."""
        raise NotImplementedError

    def set_enrollment(self, experiment, alternative):
        """Explicitly set the alternative the user is enrolled in for the specified experiment.

        This allows you to change a user between alternatives. The user and goal counts for the new
        alternative will be increment, but those for the old one will not be decremented."""
        raise NotImplementedError

    def record_goal(self, goal_name):
        """Record that this user has performed a particular goal

        This will update the goal stats for all experiments the user is enrolled in."""
        raise NotImplementedError

    def confirm_human(self):
        """Mark that this is a real human being (not a bot) and thus results should be counted"""
        pass

    def is_enrolled(self, experiment_name, alternative, request):
        """Test if the user is enrolled in the supplied alternative for the given experiment.

        The supplied alternative will be added to the list of possible alternatives for the
        experiment if it is not already there. If the user is not yet enrolled in the supplied
        experiment they will be enrolled, and an alternative chosen at random."""
        chosen_alternative = CONTROL_GROUP

        try:
            experiment = experiment_manager[experiment_name] # use cache where possible
        except KeyError:
            pass
        else:
            if experiment.is_displaying_alternatives():
                experiment.ensure_alternative_exists(alternative)

                assigned_alternative = self.get_enrollment(experiment)
                if assigned_alternative:
                    chosen_alternative = assigned_alternative
                elif experiment.is_accepting_new_users(request):
                    chosen_alternative = experiment.random_alternative()
                    self.set_enrollment(experiment, chosen_alternative)

        return alternative == chosen_alternative


class DummyUser(WebUser):
    def get_enrollment(self, experiment):
        return CONTROL_GROUP
    def set_enrollment(self, experiment, alternative):
        pass
    def record_goal(self, goal_name):
        pass
    def is_enrolled(self, experiment_name, alternative, request):
        return alternative == CONTROL_GROUP


class AuthenticatedUser(WebUser):
    def __init__(self, user):
        self.user = user
        super(AuthenticatedUser,self).__init__()

    def get_enrollment(self, experiment):
        try:
            return Enrollment.objects.get(user=self.user, experiment=experiment).alternative
        except Enrollment.DoesNotExist:
            return None

    def set_enrollment(self, experiment, alternative):
        try:
            enrollment, _ = Enrollment.objects.get_or_create(user=self.user, experiment=experiment, defaults={'alternative':alternative})
        except IntegrityError, exc:
            # Already registered (db race condition under high load)
            return
        # Update alternative if it doesn't match
        if enrollment.alternative != alternative:
            enrollment.alternative = alternative
            enrollment.save()
        experiment.increment_participant_count(alternative, self._participant_identifier())

    def record_goal(self, goal_name):
        enrollments = Enrollment.objects.filter(user=self.user)
        if not enrollments:
            return
        for enrollment in enrollments: # Looks up by PK so no point caching.
            if enrollment.experiment.is_displaying_alternatives():
                enrollment.experiment.increment_goal_count(enrollment.alternative, goal_name, self._participant_identifier())

    def _participant_identifier(self):
        return 'user:%d' % (self.user.pk,)


class SessionUser(WebUser):
    def __init__(self, session):
        self.session = session
        super(SessionUser,self).__init__()

    def get_enrollment(self, experiment):
        enrollments = self.session.get('experiments_enrollments', None)
        if enrollments and experiment.name in enrollments:
            alternative, goals = enrollments[experiment.name]
            return alternative
        return None

    def set_enrollment(self, experiment, alternative):
        enrollments = self.session.get('experiments_enrollments', {})
        enrollments[experiment.name] = (alternative, [])
        self.session['experiments_enrollments'] = enrollments
        if self._is_verified_human():
            experiment.increment_participant_count(alternative, self._participant_identifier())

    def record_goal(self, goal_name):
        if self._is_verified_human():
            enrollments = self.session.get('experiments_enrollments', None)
            if not enrollments:
                return
            for experiment_name, (alternative, goals) in enrollments.items():
                if experiment_manager[experiment_name].is_displaying_alternatives():
                    experiment_manager[experiment_name].increment_goal_count(alternative, goal_name, self._participant_identifier())
            return
        else:
            # TODO: store temp goals and convert later when is_human is triggered
            # if verify human is called quick enough this should rarely happen.
            pass

    def confirm_human(self):
        if self.session.get('experiments_verified_human', False):
            return

        self.session['experiments_verified_human'] = True

        enrollments = self.session.get('experiments_enrollments', None)
        if not enrollments:
            return

        for experiment_name, data in enrollments.items():
            alternative, goals = data
            experiment_manager[experiment_name].increment_participant_count(alternative, self._participant_identifier())

    def _participant_identifier(self):
        if not self.session.session_key:
            self.session.save() # Force session key
        return 'session:%s' % (self.session.session_key,)

    def _is_verified_human(self):
        if getattr(settings, 'EXPERIMENTS_VERIFY_HUMAN', True):
            return self.session.get('experiments_verified_human', False)
        else:
            return True
