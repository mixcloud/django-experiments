# coding=utf-8
from __future__ import division
from django.db import IntegrityError

from experiments.models import Enrollment
from experiments.manager import experiment_manager
from experiments.dateutils import now, fix_awareness, datetime_from_timestamp, timestamp_from_datetime
from experiments.signals import user_enrolled
from experiments.experiment_counters import ExperimentCounter
from experiments import conf

from collections import namedtuple
from datetime import timedelta

import collections
import numbers
import logging
import json

logger = logging.getLogger('experiments')


def participant(request=None, session=None, user=None):
    # This caches the experiment user on the request object because AuthenticatedUser can involve database lookups that
    # it caches. Signals are attached to login/logout to clear the cache using clear_participant_cache
    if request and hasattr(request, '_experiments_user'):
        return request._experiments_user
    else:
        result = _get_participant(request, session, user)
        if request:
            request._experiments_user = result
        return result


def clear_participant_cache(request):
    if hasattr(request, '_experiments_user'):
        del request._experiments_user


def _get_participant(request, session, user):
    if request and hasattr(request, 'user') and not user:
        user = request.user
    if request and hasattr(request, 'session') and not session:
        session = request.session

    if request and conf.BOT_REGEX.search(request.META.get("HTTP_USER_AGENT", "")):
        return DummyUser()
    elif user and user.is_authenticated():
        if getattr(user, 'is_confirmed_human', True):
            return AuthenticatedUser(user, request)
        else:
            return DummyUser()
    elif session:
        return SessionUser(session, request)
    else:
        return DummyUser()


EnrollmentData = namedtuple('EnrollmentData', ['experiment', 'alternative', 'enrollment_date', 'last_seen'])


class WebUser(object):
    """Represents a user (either authenticated or session based) which can take part in experiments"""

    def __init__(self):
        self.experiment_counter = ExperimentCounter()

    def enroll(self, experiment_name, alternatives, force_alternative=None):
        """
        Enroll this user in the experiment if they are not already part of it. Returns the selected alternative

        force_alternative: Optionally force a user in an alternative at enrollment time
        """
        chosen_alternative = conf.CONTROL_GROUP

        experiment = experiment_manager.get_experiment(experiment_name)

        if experiment:

            if not experiment.is_displaying_alternatives():
                return experiment.default_alternative

            if not isinstance(alternatives, collections.Mapping):
                if any(':' in alt for alt in alternatives):
                    parsed_alternatives = {}
                    for alt in alternatives:
                        try:
                            name, weight = alt.split(':', 1)
                        except ValueError:
                            name, weight = alt, None
                        else:
                            weight = int(weight)
                        parsed_alternatives[name] = weight
                    alternatives = parsed_alternatives

            if isinstance(alternatives, collections.Mapping):
                if conf.CONTROL_GROUP not in alternatives:
                    total_weight = sum(filter(
                        alt.get('weight') for alt in alternatives.values()))
                    average_weight = round(total_weight / len(alternatives))
                    experiment.ensure_alternative_exists(
                        conf.CONTROL_GROUP, average_weight)
                for alternative, weight in alternatives.items():
                    experiment.ensure_alternative_exists(alternative, weight)

            else:
                alternatives_including_control = alternatives + [conf.CONTROL_GROUP]
                for alternative in alternatives_including_control:
                    experiment.ensure_alternative_exists(alternative)

            assigned_alternative = self._get_enrollment(experiment)
            if assigned_alternative:
                chosen_alternative = assigned_alternative
            elif experiment.is_accepting_new_users():
                if force_alternative:
                    chosen_alternative = force_alternative
                else:
                    chosen_alternative = experiment.random_alternative()
                self._set_enrollment(experiment, chosen_alternative)

        return chosen_alternative

    def get_alternative(self, experiment_name):
        """
        Get the alternative this user is enrolled in.
        """
        experiment = None
        try:
            # catching the KeyError instead of using .get so that the experiment is auto created if desired
            experiment = experiment_manager[experiment_name]
        except KeyError:
            pass
        if experiment:
            if experiment.is_displaying_alternatives():
                alternative = self._get_enrollment(experiment)
                if alternative is not None:
                    return alternative
            else:
                return experiment.default_alternative
        return conf.CONTROL_GROUP

    def set_alternative(self, experiment_name, alternative):
        """Explicitly set the alternative the user is enrolled in for the specified experiment.

        This allows you to change a user between alternatives. The user and goal counts for the new
        alternative will be increment, but those for the old one will not be decremented. The user will
        be enrolled in the experiment even if the experiment would not normally accept this user."""
        experiment = experiment_manager.get_experiment(experiment_name)
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
                goals = self.experiment_counter.participant_goal_frequencies(enrollment.experiment, enrollment.alternative, other_user._participant_identifier())
                for goal_name, count in goals:
                    self.experiment_counter.increment_goal_count(enrollment.experiment, enrollment.alternative, goal_name, self._participant_identifier(), count)
            other_user._cancel_enrollment(enrollment.experiment)

    def visit(self):
        """Record that the user has visited the site for the purposes of retention tracking"""
        for enrollment in self._get_all_enrollments():
            if enrollment.experiment.is_displaying_alternatives():
                # We have two different goals, VISIT_NOT_PRESENT_COUNT_GOAL and VISIT_PRESENT_COUNT_GOAL.
                # VISIT_PRESENT_COUNT_GOAL will avoid firing on the first time we set last_seen as it is assumed that the user is
                # on the page and therefore it would automatically trigger and be valueless.
                # This should be used for experiments when we enroll the user as part of the pageview,
                # alternatively we can use the NOT_PRESENT GOAL which will increment on the first pageview,
                # this is mainly useful for notification actions when the users isn't initially present.

                if not enrollment.last_seen:
                    self._experiment_goal(enrollment.experiment, enrollment.alternative, conf.VISIT_NOT_PRESENT_COUNT_GOAL, 1)
                    self._set_last_seen(enrollment.experiment, now())
                elif now() - enrollment.last_seen >= timedelta(hours=conf.SESSION_LENGTH):
                    self._experiment_goal(enrollment.experiment, enrollment.alternative, conf.VISIT_NOT_PRESENT_COUNT_GOAL, 1)
                    self._experiment_goal(enrollment.experiment, enrollment.alternative, conf.VISIT_PRESENT_COUNT_GOAL, 1)
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

    def is_enrolled(self, experiment_name, alternative):
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

    def _experiment_goal(self, experiment, alternative, goal_name, count):
        "Record a goal against a particular experiment and alternative"
        raise NotImplementedError

    def _set_last_seen(self, experiment, last_seen):
        "Set the last time the user was seen associated with this experiment"
        raise NotImplementedError


class DummyUser(WebUser):
    def _get_enrollment(self, experiment):
        return None

    def _set_enrollment(self, experiment, alternative, enrollment_date=None, last_seen=None):
        pass

    def is_enrolled(self, experiment_name, alternative):
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
        super(AuthenticatedUser, self).__init__()

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
            enrollment, _ = Enrollment.objects.get_or_create(user=self.user, experiment=experiment, defaults={'alternative': alternative})
        except IntegrityError:
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

        self.experiment_counter.increment_participant_count(experiment, alternative, self._participant_identifier())

        user_enrolled.send(self, experiment=experiment.name, alternative=alternative, user=self.user, session=None)

    def _participant_identifier(self):
        return 'user:%d' % (self.user.pk, )

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
            self.experiment_counter.remove_participant(experiment, enrollment.alternative, self._participant_identifier())
            enrollment.delete()

    def _experiment_goal(self, experiment, alternative, goal_name, count):
        self.experiment_counter.increment_goal_count(experiment, alternative, goal_name, self._participant_identifier(), count)

    def _set_last_seen(self, experiment, last_seen):
        Enrollment.objects.filter(user=self.user, experiment=experiment).update(last_seen=last_seen)


def _session_enrollment_latest_version(data):
    try:
        alternative, unused, enrollment_date, last_seen = data
        if isinstance(enrollment_date, numbers.Number):
            enrollment_date = datetime_from_timestamp(enrollment_date)
        if isinstance(last_seen, numbers.Number):
            last_seen = datetime_from_timestamp(last_seen)
        if last_seen:
            last_seen = fix_awareness(last_seen)
    except ValueError:  # Data from previous version
        alternative, unused = data
        enrollment_date = None
        last_seen = None
    return alternative, unused, enrollment_date, last_seen


class SessionUser(WebUser):
    def __init__(self, session, request=None):
        self.session = session
        self.request = request
        super(SessionUser, self).__init__()

    def _get_enrollment(self, experiment):
        enrollments = self.session.get('experiments_enrollments', None)
        if enrollments and experiment.name in enrollments:
            alternative, _, _, _ = _session_enrollment_latest_version(enrollments[experiment.name])
            return alternative
        return None

    def _set_enrollment(self, experiment, alternative, enrollment_date=None, last_seen=None):
        enrollments = self.session.get('experiments_enrollments', {})
        enrollments[experiment.name] = (alternative, None, timestamp_from_datetime(enrollment_date or now()), timestamp_from_datetime(last_seen))
        self.session['experiments_enrollments'] = enrollments
        if self._is_verified_human():
            self.experiment_counter.increment_participant_count(experiment, alternative, self._participant_identifier())
        else:
            logger.info(json.dumps({'type':'participant_unconfirmed', 'experiment': experiment.name, 'alternative': alternative, 'participant': self._participant_identifier()}))

        user_enrolled.send(self, experiment=experiment.name, alternative=alternative, user=None, session=self.session)

    def confirm_human(self):
        self.session[conf.CONFIRM_HUMAN_SESSION_KEY] = True
        logger.info(json.dumps({'type': 'confirm_human', 'participant': self._participant_identifier()}))

        # Replay enrollments
        for enrollment in self._get_all_enrollments():
            self.experiment_counter.increment_participant_count(enrollment.experiment, enrollment.alternative, self._participant_identifier())

        # Replay goals
        if 'experiments_goals' in self.session:
            try:
                for experiment_name, alternative, goal_name, count in self.session['experiments_goals']:
                    experiment = experiment_manager.get_experiment(experiment_name)
                    if experiment:
                        self.experiment_counter.increment_goal_count(experiment, alternative, goal_name, self._participant_identifier(), count)
            except ValueError:
                pass  # Values from older version
            finally:
                del self.session['experiments_goals']

    def _participant_identifier(self):
        if 'experiments_session_key' not in self.session:
            if not self.session.session_key:
                self.session.save()  # Force session key
            self.session['experiments_session_key'] = self.session.session_key
        return 'session:%s' % (self.session['experiments_session_key'], )

    def _is_verified_human(self):
        if conf.VERIFY_HUMAN:
            return self.session.get(conf.CONFIRM_HUMAN_SESSION_KEY, False)
        else:
            return True

    def _get_all_enrollments(self):
        enrollments = self.session.get('experiments_enrollments', None)
        if enrollments:
            for experiment_name, data in list(enrollments.items()):
                alternative, _, enrollment_date, last_seen = _session_enrollment_latest_version(data)
                experiment = experiment_manager.get_experiment(experiment_name)
                if experiment:
                    yield EnrollmentData(experiment, alternative, enrollment_date, last_seen)

    def _cancel_enrollment(self, experiment):
        alternative = self._get_enrollment(experiment)
        if alternative:
            self.experiment_counter.remove_participant(experiment, alternative, self._participant_identifier())
            enrollments = self.session.get('experiments_enrollments', None)
            del enrollments[experiment.name]
            self.session['experiments_enrollments'] = enrollments

    def _experiment_goal(self, experiment, alternative, goal_name, count):
        if self._is_verified_human():
            self.experiment_counter.increment_goal_count(experiment, alternative, goal_name, self._participant_identifier(), count)
        else:
            goals = self.session.get('experiments_goals', [])
            goals.append((experiment.name, alternative, goal_name, count))
            self.session['experiments_goals'] = goals
            logger.info(json.dumps({'type': 'goal_hit_unconfirmed', 'goal': goal_name, 'goal_count': count, 'experiment': experiment.name, 'alternative': alternative, 'participant': self._participant_identifier()}))

    def _set_last_seen(self, experiment, last_seen):
        enrollments = self.session.get('experiments_enrollments', {})
        alternative, unused, enrollment_date, _ = _session_enrollment_latest_version(enrollments[experiment.name])
        enrollments[experiment.name] = (alternative, unused, timestamp_from_datetime(enrollment_date), timestamp_from_datetime(last_seen))
        self.session['experiments_enrollments'] = enrollments


__all__ = ['participant']
