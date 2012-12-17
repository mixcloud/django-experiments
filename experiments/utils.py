from django.conf import settings
from django.db import IntegrityError
from django.contrib.auth.models import User
from django.contrib.sessions.backends.base import SessionBase

from experiments.models import Enrollment, CONTROL_GROUP
from experiments.manager import experiment_manager

import re
import warnings


# Known bots user agents to drop from experiments
BOT_REGEX = re.compile("(Baidu|Gigabot|Googlebot|YandexBot|AhrefsBot|TVersity|libwww-perl|Yeti|lwp-trivial|msnbot|bingbot|facebookexternalhit|Twitterbot|Twitmunin|SiteUptime|TwitterFeed|Slurp|WordPress|ZIBB|ZyBorg)", re.IGNORECASE)


def record_goal(request, goal_name):
    _record_goal(goal_name, request)


def _record_goal(goal_name, request=None, session=None, user=None):
    warnings.warn('record_goal is deprecated. Please use participant().goal() instead.', DeprecationWarning)
    experiment_user = participant(request, session, user)
    experiment_user.goal(goal_name)


def participant(request=None, session=None, user=None):
    if request and hasattr(request, 'user') and not user:
        user = request.user
    if request and hasattr(request, 'session') and not session:
        session = request.session

    if request and BOT_REGEX.search(request.META.get("HTTP_USER_AGENT","")):
        return DummyUser()
    elif user and user.is_authenticated():
        return AuthenticatedUser(user, request)
    elif session:
        return SessionUser(session, request)
    else:
        return DummyUser()


class WebUser(object):
    """Represents a user (either authenticated or session based) which can take part in experiments"""

    def enroll(self, experiment_name, alternatives):
        """Enroll this user in the experiment if they are not already part of it. Returns the selected alternative"""
        chosen_alternative = CONTROL_GROUP

        experiment = experiment_manager.get(experiment_name, None)
        if experiment and experiment.is_displaying_alternatives():
            alternatives_including_control = alternatives + [CONTROL_GROUP]
            for alternative in alternatives_including_control:
                experiment.ensure_alternative_exists(alternative)

            assigned_alternative = self._get_enrollment(experiment)
            if assigned_alternative:
                chosen_alternative = assigned_alternative
            elif experiment.is_accepting_new_users(self._gargoyle_key()):
                chosen_alternative = experiment.random_alternative()
                self._set_enrollment(experiment, chosen_alternative)

        return chosen_alternative

    def get_alternative(self, experiment_name):
        """Get the alternative this use is enrolled in. If not enrolled in the experiment returns 'control'"""
        experiment = experiment_manager.get(experiment_name, None)
        if experiment and experiment.is_displaying_alternatives():
            alternative = self._get_enrollment(experiment)
            if alternative is not None:
                return alternative
        return 'control'

    def set_alternative(self, experiment_name, alternative):
        """Explicitly set the alternative the user is enrolled in for the specified experiment.

        This allows you to change a user between alternatives. The user and goal counts for the new
        alternative will be increment, but those for the old one will not be decremented. The user will
        be enrolled in the experiment even if the experiment would not normally accept this user."""
        experiment = experiment_manager.get(experiment_name, None)
        if experiment:
            self._set_enrollment(experiment, alternative)

    def goal(self, goal_name, count=1):
        """Record that this user has performed a particular goal

        This will update the goal stats for all experiments the user is enrolled in."""
        raise NotImplementedError

    def confirm_human(self):
        """Mark that this is a real human being (not a bot) and thus results should be counted"""
        pass

    def incorporate(self, other_user):
        """Incorporate all enrollments and goals performed by the other user

        If this user is not enrolled in a given experiment, the results for the
        other user are incorporated. For experiments this user is already
        enrolled in the results of the other user are discarded.

        This takes a relatively large amount of time for each experiment the other
        user is enrolled in."""
        for experiment, alternative in other_user._get_all_enrollments():
            if not self._get_enrollment(experiment):
                self._set_enrollment(experiment, alternative)
                goals = experiment.participant_goal_frequencies(alternative, other_user._participant_identifier())
                for goal_name, count in goals:
                    experiment.increment_goal_count(alternative, goal_name, self._participant_identifier(), count)
            other_user._cancel_enrollment(experiment)

    def _get_enrollment(self, experiment):
        """Get the name of the alternative this user is enrolled in for the specified experiment
        
        `experiment` is an instance of Experiment. If the user is not currently enrolled returns None."""
        raise NotImplementedError

    def _set_enrollment(self, experiment, alternative):
        """Explicitly set the alternative the user is enrolled in for the specified experiment.

        This allows you to change a user between alternatives. The user and goal counts for the new
        alternative will be increment, but those for the old one will not be decremented."""
        raise NotImplementedError

    def is_enrolled(self, experiment_name, alternative, request):
        """Enroll this user in the experiment if they are not already part of it. Returns the selected alternative"""
        """Test if the user is enrolled in the supplied alternative for the given experiment.

        The supplied alternative will be added to the list of possible alternatives for the
        experiment if it is not already there. If the user is not yet enrolled in the supplied
        experiment they will be enrolled, and an alternative chosen at random."""
        chosen_alternative = self.enroll(experiment_name, [alternative])
        return alternative == chosen_alternative

    def _participant_identifier(self):
        "Unique identifier for this user in the counter store"
        raise NotImplementedError

    def _get_all_enrollments(self):
        "Return experiment, alternative tuples for all experiments the user is enrolled in"
        raise NotImplementedError

    def _cancel_enrollment(self, experiment):
        "Remove the enrollment and any goals the user has against this experiment"
        raise NotImplementedError

    def _gargoyle_key(self):
        return None


class DummyUser(WebUser):
    def _get_enrollment(self, experiment):
        return None
    def _set_enrollment(self, experiment, alternative):
        pass
    def goal(self, goal_name, count=1):
        pass
    def is_enrolled(self, experiment_name, alternative, request):
        return alternative == CONTROL_GROUP
    def incorporate(self, other_user):
        for experiment, alternative in other_user._get_all_enrollments():
            other_user._cancel_enrollment(experiment)
    def _participant_identifier(self):
        return ""
    def _get_all_enrollments(self):
        return []
    def _is_enrolled_in_experiment(self, experiment):
        return False
    def _cancel_enrollment(self, experiment):
        pass
    def _get_goal_counts(self, experiment, alternative):
        return {}


class AuthenticatedUser(WebUser):
    def __init__(self, user, request=None):
        self.user = user
        self.request = request
        super(AuthenticatedUser,self).__init__()

    def _get_enrollment(self, experiment):
        try:
            return Enrollment.objects.get(user=self.user, experiment=experiment).alternative
        except Enrollment.DoesNotExist:
            return None

    def _set_enrollment(self, experiment, alternative):
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

    def goal(self, goal_name, count=1):
        for experiment, alternative in self._get_all_enrollments():
            if experiment.is_displaying_alternatives():
                experiment.increment_goal_count(alternative, goal_name, self._participant_identifier(), count)

    def _participant_identifier(self):
        return 'user:%d' % (self.user.pk,)

    def _get_all_enrollments(self):
        enrollments = Enrollment.objects.filter(user=self.user).select_related("experiment")
        if enrollments:
            for enrollment in enrollments:
                yield enrollment.experiment, enrollment.alternative

    def _cancel_enrollment(self, experiment):
        try:
            enrollment = Enrollment.objects.get(user=self.user, experiment=experiment)
        except Enrollment.DoesNotExist:
            pass
        else:
            experiment.remove_participant(enrollment.alternative, self._participant_identifier())
            enrollment.delete()

    def _gargoyle_key(self):
        return self.request or self.user


class SessionUser(WebUser):
    def __init__(self, session, request=None):
        self.session = session
        self.request = request
        super(SessionUser,self).__init__()

    def _get_enrollment(self, experiment):
        enrollments = self.session.get('experiments_enrollments', None)
        if enrollments and experiment.name in enrollments:
            alternative, goals = enrollments[experiment.name]
            return alternative
        return None

    def _set_enrollment(self, experiment, alternative):
        enrollments = self.session.get('experiments_enrollments', {})
        enrollments[experiment.name] = (alternative, [])
        self.session['experiments_enrollments'] = enrollments
        if self._is_verified_human():
            experiment.increment_participant_count(alternative, self._participant_identifier())

    def goal(self, goal_name, count=1):
        if self._is_verified_human():
            for experiment, alternative in self._get_all_enrollments():
                if experiment.is_displaying_alternatives():
                    experiment.increment_goal_count(alternative, goal_name, self._participant_identifier(), count)
        else:
            goals = self.session.get('experiments_goals', [])
            goals.append(goal_name) # Note, duplicates are allowed
            self.session['experiments_goals'] = goals

    def confirm_human(self):
        if self.session.get('experiments_verified_human', False):
            return

        self.session['experiments_verified_human'] = True

        # Replay enrollments
        for experiment, alternative in self._get_all_enrollments():
            experiment.increment_participant_count(alternative, self._participant_identifier())

        # Replay goals
        if 'experiments_goals' in self.session:
            for goal_name in self.session['experiments_goals']:
                self.goal(goal_name) # Now we have verified human, these will be set
            del self.session['experiments_goals']

    def _participant_identifier(self):
        if 'experiments_session_key' not in self.session:
            if not self.session.session_key:
                self.session.save() # Force session key
            self.session['experiments_session_key'] = self.session.session_key
        return 'session:%s' % (self.session['experiments_session_key'],)

    def _is_verified_human(self):
        if getattr(settings, 'EXPERIMENTS_VERIFY_HUMAN', True):
            return self.session.get('experiments_verified_human', False)
        else:
            return True

    def _get_all_enrollments(self):
        enrollments = self.session.get('experiments_enrollments', None)
        if enrollments:
            for experiment_name, data in enrollments.items():
                alternative, _ = data
                experiment = experiment_manager.get(experiment_name, None)
                if experiment:
                    yield experiment, alternative

    def _cancel_enrollment(self, experiment):
        alternative = self._get_enrollment(experiment)
        if alternative:
            experiment.remove_participant(alternative, self._participant_identifier())
            enrollments = self.session.get('experiments_enrollments', None)
            del enrollments[experiment.name]

    def _gargoyle_key(self):
        return self.request

__all__ = ['participant', 'record_goal']
