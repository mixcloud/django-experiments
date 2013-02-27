from django.db import IntegrityError
from django.contrib.auth.models import User
from django.contrib.sessions.backends.base import SessionBase

from experiments.models import Enrollment
from experiments.manager import experiment_manager
from experiments.dateutils import now
from experiments import conf

from collections import namedtuple

import re
import warnings
import collections
from datetime import timedelta

# Known bots user agents to drop from experiments


def record_goal(request, goal_name):
    _record_goal(goal_name, request)


def _record_goal(goal_name, request=None, session=None, user=None):
    warnings.warn('record_goal is deprecated. Please use participant().goal() instead.', DeprecationWarning)
    experiment_user = participant(request, session, user)
    experiment_user.goal(goal_name)


def participant(request=None, session=None, user=None):
    if request and hasattr(request, '_experiments_user'):
        return request._experiments_user
    else:
        result = _get_participant(request, session, user)
        if request:
            request._experiments_user = result
        return result


def _get_participant(request, session, user):
    if request and hasattr(request, 'user') and not user:
        user = request.user
    if request and hasattr(request, 'session') and not session:
        session = request.session

    if request and conf.BOT_REGEX.search(request.META.get("HTTP_USER_AGENT","")):
        return DummyUser()
    elif user and user.is_authenticated():
        return AuthenticatedUser(user, request)
    elif session:
        return SessionUser(session, request)
    else:
        return DummyUser()

EnrollmentData = namedtuple('EnrollmentData', ['experiment', 'alternative', 'enrollment_date', 'last_seen'])

class WebUser(object):
    """Represents a user (either authenticated or session based) which can take part in experiments"""

    def enroll(self, experiment_name, alternatives, selected_alternative=None):
        """Enroll this user in the experiment if they are not already part of it. Returns the selected alternative"""
        chosen_alternative = conf.CONTROL_GROUP

        # Grab experiment from cache
        try:
            experiment = experiment_manager[experiment_name]
        except KeyError:  # thrown if EXPERIMENTS_AUTO_CREATE == False
            return conf.CONTROL_GROUP

        if experiment and experiment.is_displaying_alternatives():
            if isinstance(alternatives, collections.Mapping):
                if conf.CONTROL_GROUP not in alternatives:
                    experiment.ensure_alternative_exists(conf.CONTROL_GROUP, 1)
                for alternative, weight in alternatives.items():
                    experiment.ensure_alternative_exists(alternative, weight)
            else:
                alternatives_including_control = alternatives + [conf.CONTROL_GROUP]
                for alternative in alternatives_including_control:
                    experiment.ensure_alternative_exists(alternative)

            assigned_alternative = self._get_enrollment(experiment)
            if assigned_alternative:
                chosen_alternative = assigned_alternative
            elif experiment.is_accepting_new_users(self._gargoyle_key()):
                if selected_alternative:
                    chosen_alternative = selected_alternative
                else:
                    chosen_alternative = experiment.random_alternative()
                self._set_enrollment(experiment, chosen_alternative)

        return chosen_alternative

    def get_alternative(self, experiment_name):
        """Get the alternative this user is enrolled in. If not enrolled in the experiment returns 'control'"""
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
        for enrollment in self._get_all_enrollments():
            if enrollment.experiment.is_displaying_alternatives():
                self._experiment_goal(enrollment.experiment, enrollment.alternative, goal_name, count)

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
        for enrollment in other_user._get_all_enrollments():
            if not self._get_enrollment(enrollment.experiment):
                self._set_enrollment(enrollment.experiment, enrollment.alternative, enrollment.enrollment_date, enrollment.last_seen)
                goals = enrollment.experiment.participant_goal_frequencies(enrollment.alternative, other_user._participant_identifier())
                for goal_name, count in goals:
                    enrollment.experiment.increment_goal_count(enrollment.alternative, goal_name, self._participant_identifier(), count)
            other_user._cancel_enrollment(enrollment.experiment)

    def visit(self):
        """Record that the user has visited the site for the purposes of retention tracking"""
        for enrollment in self._get_all_enrollments():
            if enrollment.experiment.is_displaying_alternatives():
                if not enrollment.last_seen or now() - enrollment.last_seen >= timedelta(1):
                    self._experiment_goal(enrollment.experiment, enrollment.alternative, conf.VISIT_COUNT_GOAL, 1)
                    self._set_last_seen(enrollment.experiment, now())

    def _get_enrollment(self, experiment):
        """Get the name of the alternative this user is enrolled in for the specified experiment
        
        `experiment` is an instance of Experiment. If the user is not currently enrolled returns None."""
        raise NotImplementedError

    def _set_enrollment(self, experiment, alternative, enrollment_date=None, last_seen=None):
        """Explicitly set the alternative the user is enrolled in for the specified experiment.

        This allows you to change a user between alternatives. The user and goal counts for the new
        alternative will be increment, but those for the old one will not be decremented."""
        raise NotImplementedError

    def is_enrolled(self, experiment_name, alternative, request, selected_alternative=None):
        """Enroll this user in the experiment if they are not already part of it. Returns the selected alternative"""
        """Test if the user is enrolled in the supplied alternative for the given experiment.

        The supplied alternative will be added to the list of possible alternatives for the
        experiment if it is not already there. If the user is not yet enrolled in the supplied
        experiment they will be enrolled, and an alternative chosen at random."""
        chosen_alternative = self.enroll(experiment_name, [alternative], selected_alternative)
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

    def _experiment_goal(self, experiment, alternative, goal_name, count):
        "Record a goal against a particular experiment and alternative"
        raise NotImplementedError

    def _set_last_seen(self, experiment, last_seen):
        "Set the last time the user was seen associated with this experiment"
        raise NotImplementedError

    def _gargoyle_key(self):
        return None


class DummyUser(WebUser):
    def _get_enrollment(self, experiment):
        return None
    def _set_enrollment(self, experiment, alternative, enrollment_date=None, last_seen=None):
        pass
    def is_enrolled(self, experiment_name, alternative, request, selected_alternative=None):
        return alternative == conf.CONTROL_GROUP
    def incorporate(self, other_user):
        for enrollment in other_user._get_all_enrollments():
            other_user._cancel_enrollment(enrollment.experiment)
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
    def _experiment_goal(self, experiment, alternative, goal_name, count):
        pass
    def _set_last_seen(self, experiment, last_seen):
        pass


class AuthenticatedUser(WebUser):
    def __init__(self, user, request=None):
        self._enrollment_cache = {}
        self.user = user
        self.request = request
        super(AuthenticatedUser,self).__init__()

    def _get_enrollment(self, experiment):
        if experiment.name not in self._enrollment_cache:
            try:
                self._enrollment_cache[experiment.name] = Enrollment.objects.get(user=self.user, experiment=experiment).alternative
            except Enrollment.DoesNotExist:
                self._enrollment_cache[experiment.name] = None
        return self._enrollment_cache[experiment.name]

    def _set_enrollment(self, experiment, alternative, enrollment_date=None, last_seen=None):
        if experiment.name in self._enrollment_cache:
            del self._enrollment_cache[experiment.name]

        try:
            enrollment, _ = Enrollment.objects.get_or_create(user=self.user, experiment=experiment, defaults={'alternative':alternative})
        except IntegrityError, exc:
            # Already registered (db race condition under high load)
            return
        # Update alternative if it doesn't match
        enrollment_changed = False
        if enrollment.alternative != alternative:
            enrollment.alternative = alternative
            enrollment_changed = True
        if enrollment_date:
            enrollment.enrollment_date = enrollment_date
            enrollment_changed = True
        if last_seen:
            enrollment.last_seen = last_seen
            enrollment_changed = True

        if enrollment_changed:
            enrollment.save()

        experiment.increment_participant_count(alternative, self._participant_identifier())

    def _participant_identifier(self):
        return 'user:%d' % (self.user.pk,)

    def _get_all_enrollments(self):
        enrollments = Enrollment.objects.filter(user=self.user).select_related("experiment")
        if enrollments:
            for enrollment in enrollments:
                yield EnrollmentData(enrollment.experiment, enrollment.alternative, enrollment.enrollment_date, enrollment.last_seen)

    def _cancel_enrollment(self, experiment):
        try:
            enrollment = Enrollment.objects.get(user=self.user, experiment=experiment)
        except Enrollment.DoesNotExist:
            pass
        else:
            experiment.remove_participant(enrollment.alternative, self._participant_identifier())
            enrollment.delete()

    def _experiment_goal(self, experiment, alternative, goal_name, count):
        experiment.increment_goal_count(alternative, goal_name, self._participant_identifier(), count)

    def _set_last_seen(self, experiment, last_seen):
        Enrollment.objects.filter(user=self.user, experiment=experiment).update(last_seen=last_seen)

    def _gargoyle_key(self):
        return self.request or self.user

def _session_enrollment_latest_version(data):
    try:
        alternative, unused, enrollment_date, last_seen = data
    except ValueError: # Data from previous version
        alternative, unused = data
        enrollment_date = None
        last_seen = None
    return alternative, unused, enrollment_date, last_seen


class SessionUser(WebUser):
    def __init__(self, session, request=None):
        self.session = session
        self.request = request
        super(SessionUser,self).__init__()

    def _get_enrollment(self, experiment):
        enrollments = self.session.get('experiments_enrollments', None)
        if enrollments and experiment.name in enrollments:
            alternative, _, _, _ = _session_enrollment_latest_version(enrollments[experiment.name])
            return alternative
        return None

    def _set_enrollment(self, experiment, alternative, enrollment_date=None, last_seen=None):
        enrollments = self.session.get('experiments_enrollments', {})
        enrollments[experiment.name] = (alternative, None, enrollment_date or now(), last_seen)
        self.session['experiments_enrollments'] = enrollments
        if self._is_verified_human():
            experiment.increment_participant_count(alternative, self._participant_identifier())

    def confirm_human(self):
        if self.session.get('experiments_verified_human', False):
            return

        self.session['experiments_verified_human'] = True

        # Replay enrollments
        for enrollment in self._get_all_enrollments():
            enrollment.experiment.increment_participant_count(enrollment.alternative, self._participant_identifier())

        # Replay goals
        if 'experiments_goals' in self.session:
            try:
                for experiment_name, alternative, goal_name, count in self.session['experiments_goals']:
                    experiment = experiment_manager.get(experiment_name, None)
                    if experiment:
                        experiment.increment_goal_count(alternative, goal_name, self._participant_identifier(), count)
            except ValueError:
                pass # Values from older version
            finally:
                del self.session['experiments_goals']

    def _participant_identifier(self):
        if 'experiments_session_key' not in self.session:
            if not self.session.session_key:
                self.session.save() # Force session key
            self.session['experiments_session_key'] = self.session.session_key
        return 'session:%s' % (self.session['experiments_session_key'],)

    def _is_verified_human(self):
        if conf.VERIFY_HUMAN:
            return self.session.get('experiments_verified_human', False)
        else:
            return True

    def _get_all_enrollments(self):
        enrollments = self.session.get('experiments_enrollments', None)
        if enrollments:
            for experiment_name, data in enrollments.items():
                alternative, _, enrollment_date, last_seen = _session_enrollment_latest_version(data)
                experiment = experiment_manager.get(experiment_name, None)
                if experiment:
                    yield EnrollmentData(experiment, alternative, enrollment_date, last_seen)

    def _cancel_enrollment(self, experiment):
        alternative = self._get_enrollment(experiment)
        if alternative:
            experiment.remove_participant(alternative, self._participant_identifier())
            enrollments = self.session.get('experiments_enrollments', None)
            del enrollments[experiment.name]

    def _experiment_goal(self, experiment, alternative, goal_name, count):
        if self._is_verified_human():
            experiment.increment_goal_count(alternative, goal_name, self._participant_identifier(), count)
        else:
            goals = self.session.get('experiments_goals', [])
            goals.append( (experiment.name, alternative, goal_name, count) )
            self.session['experiments_goals'] = goals

    def _set_last_seen(self, experiment, last_seen):
        enrollments = self.session.get('experiments_enrollments', {})
        alternative, unused, enrollment_date, _ = _session_enrollment_latest_version(enrollments[experiment.name])
        enrollments[experiment.name] = (alternative, unused, enrollment_date, last_seen)
        self.session['experiments_enrollments'] = enrollments

    def _gargoyle_key(self):
        return self.request


__all__ = ['participant', 'record_goal']
