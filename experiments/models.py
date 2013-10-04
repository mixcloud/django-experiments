import random

from django.core.urlresolvers import reverse
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings
from django.utils import simplejson as json
from django.utils.safestring import mark_safe

from jsonfield import JSONField

import waffle
from waffle import Flag

from experiments import counters, conf, forms
from experiments.dateutils import now

PARTICIPANT_KEY = '%s:%s:participant'
GOAL_KEY = '%s:%s:%s:goal'

CONTROL_STATE = 0  # The experiment is essentially disabled.
                   # All users will see the control alternative, and no data
                   # will be collected.
ENABLED_STATE = 1  # The experiment is enabled globally, for all users.
SWITCH_STATE = 2   # If a switch_key is specified, the experiment will rely on
                   # the switch/flag to determine if the user is included in
                   # the experiment.
TRACK_STATE = 3    # The experiment is enabled globally,
                   # but no new users are accepted.

STATES = (
    (CONTROL_STATE, 'Control'),
    (ENABLED_STATE, 'Enabled'),
    (SWITCH_STATE, 'Switch'),
    (TRACK_STATE, 'Track'),
)


class MultiSelectField(models.Field):
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        self.max_choices = kwargs.pop('max_choices', 0)
        super(MultiSelectField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return "CharField"

    def get_choices_default(self):
        return self.get_choices(include_blank=False)

    def _get_FIELD_display(self, field):
        value = getattr(self, field.attname)
        choicedict = dict(field.choices)

    def formfield(self, **kwargs):
        # don't call super, as that overrides default widget if it has choices
        defaults = {
            'required': not self.blank,
            'label': self.verbose_name,
            'help_text': self.help_text,
            'choices': self.choices,
            'max_choices': self.max_choices,
        }
        if self.has_default():
            defaults['initial'] = self.get_default()
        defaults.update(kwargs)
        return forms.MultiSelectFormField(**defaults)

    def validate(self, value, model_instance):
        '''Overwrite standard to allow validation a list of values '''
        if isinstance(value, (list, tuple, set, frozenset)):
            for v in value:
                super(MultiSelectField, self).validate(v, model_instance)
        else:
            super(MultiSelectField, self).validate(value, model_instance)

    def get_db_prep_value(self, value, connection, prepared=False):
        if isinstance(value, basestring):
            return value
        if isinstance(value, (list, tuple, set, frozenset)):
            return ",".join(value)

    def to_python(self, value):
        if isinstance(value, (list, tuple, set, frozenset)):
            return value
        return value.split(",")

    def contribute_to_class(self, cls, name):
        super(MultiSelectField, self).contribute_to_class(cls, name)
        if self.choices:
            func = lambda self, fieldname=name, choicedict=dict(
                self.choices): ",".join(
                    [choicedict.get(value, value)
                     for value in getattr(self, fieldname)])
            setattr(cls, 'get_%s_display' % self.name, func)


class Experiment(models.Model):
    name = models.CharField(
        primary_key=True, max_length=128,
        help_text='The experiment name.')
    description = models.TextField(
        default="", blank=True, null=True,
        help_text='A brief description of this experiment.')
    alternatives = JSONField(default={}, blank=True)
    relevant_chi2_goals = MultiSelectField(
        default="", null=True, blank=True,
        choices=((goal, goal) for goal in conf.ALL_GOALS),
        verbose_name='Chi-squared test',
        help_text=mark_safe(
            '<a href="http://en.wikipedia.org/wiki/Chi-squared_test" '
            'target="_blank">Used when optimising for conversion rate.</a>'))
    relevant_mwu_goals = MultiSelectField(
        default="", null=True, blank=True,
        choices=((goal, goal) for goal in conf.ALL_GOALS),
        verbose_name='Mann-Whitney U',
        help_text=mark_safe(
            '<a href="http://en.wikipedia.org/wiki/Mann%E2%80%93Whitney_U" '
            'target="_blank">Used when optimising for number of times '
            'users perform an action. (Advanced)</a>'))
    switch_key = models.CharField(
        default="", max_length=50, null=True, blank=True,
        help_text='Connected to a feature switch. (Optional)')
    state = models.IntegerField(default=CONTROL_STATE, choices=STATES)
    start_date = models.DateTimeField(default=now, blank=True, null=True, db_index=True)
    end_date = models.DateTimeField(blank=True, null=True)

    @staticmethod
    def enabled_experiments():
        return Experiment.objects.filter(
            state__in=[ENABLED_STATE, SWITCH_STATE])

    def is_displaying_alternatives(self):
        if self.state == CONTROL_STATE:
            return False
        if self.state == ENABLED_STATE:
            return True
        if self.state == SWITCH_STATE:
            return True
        if self.state == TRACK_STATE:
            return True
        raise Exception("Invalid experiment state %s!" % self.state)

    def is_accepting_new_users(self, request):
        if self.state == CONTROL_STATE:
            return False
        if self.state == ENABLED_STATE:
            return True
        if self.state == SWITCH_STATE:
            return waffle.flag_is_active(request, self.switch_key)
        if self.state == TRACK_STATE:
            return False
        raise Exception("Invalid experiment state %s!" % self.state)

    @property
    def switch(self):
        if self.switch_key and conf.SWITCH_AUTO_CREATE:
            try:
                return Flag.objects.get(name=self.switch_key)
            except Flag.DoesNotExist:
                pass
        return None

    def ensure_alternative_exists(self, alternative, weight=None):
        if alternative not in self.alternatives:
            self.alternatives[alternative] = {}
            self.alternatives[alternative]['enabled'] = True
            self.save()
        if (weight is not None
                and 'weight' not in self.alternatives[alternative]):
            self.alternatives[alternative]['weight'] = float(weight)
            self.save()

    def random_alternative(self):
        if all('weight' in alt for alt in self.alternatives.values()):
            return weighted_choice(
                [(name, details['weight'])
                 for name, details in self.alternatives.items()])
        return random.choice(self.alternatives.keys())

    def increment_participant_count(self, alternative_name,
                                    participant_identifier):
        # Increment experiment_name:alternative:participant counter
        counter_key = PARTICIPANT_KEY % (self.name, alternative_name)
        counters.increment(counter_key, participant_identifier)

    def increment_goal_count(self, alternative_name, goal_name,
                             participant_identifier, count=1):
        # Increment experiment_name:alternative:participant counter
        counter_key = GOAL_KEY % (self.name, alternative_name, goal_name)
        counters.increment(counter_key, participant_identifier, count)

    def remove_participant(self, alternative_name, participant_identifier):
        # Remove participation record
        counter_key = PARTICIPANT_KEY % (self.name, alternative_name)
        counters.clear(counter_key, participant_identifier)

        # Remove goal records
        for goal_name in conf.ALL_GOALS:
            counter_key = GOAL_KEY % (self.name, alternative_name, goal_name)
            counters.clear(counter_key, participant_identifier)

    def participant_count(self, alternative):
        return counters.get(PARTICIPANT_KEY % (self.name, alternative))

    def goal_count(self, alternative, goal):
        return counters.get(GOAL_KEY % (self.name, alternative, goal))

    def participant_goal_frequencies(self, alternative,
                                     participant_identifier):
        for goal in conf.ALL_GOALS:
            yield goal, counters.get_frequency(
                GOAL_KEY % (self.name, alternative, goal),
                participant_identifier)

    def goal_distribution(self, alternative, goal):
        return counters.get_frequencies(
            GOAL_KEY % (self.name, alternative, goal))

    def __unicode__(self):
        return self.name

    def to_dict(self):
        info = self._meta.app_label, self._meta.module_name
        data = {
            'name': self.name,
            'edit_url': reverse('admin:%s_%s_results' % info,
                                args=(self.name,)),
            'start_date': self.start_date,
            'end_date': self.end_date,
            'state': self.state,
            'switch_key': self.switch_key,
            'description': self.description,
            'relevant_chi2_goals': self.relevant_chi2_goals,
            'relevant_mwu_goals': self.relevant_mwu_goals,
        }
        return data

    def to_dict_serialized(self):
        return json.dumps(self.to_dict(), cls=DjangoJSONEncoder)

    def save(self, *args, **kwargs):
        # Create new flag
        if self.switch_key and conf.SWITCH_AUTO_CREATE:
            try:
                Flag.objects.get(name=self.switch_key)
            except Flag.DoesNotExist:
                Flag.objects.create(
                    name=self.switch_key,
                    note=self.description)

        if not self.switch_key and self.state == 2:
            self.state = 0

        if self.state == 0:
            self.end_date = now()
        else:
            self.end_date = None

        super(Experiment, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Delete existing enrollments
        self.enrollment_set.all().delete()

        # Delete existing flag
        if self.switch_key and conf.SWITCH_AUTO_CREATE:
            try:
                Flag.objects.filter(name=self.switch_key).delete()
            except Flag.DoesNotExist:
                pass

        counters.reset_pattern(self.name + "*")

        super(Experiment, self).delete(*args, **kwargs)


class Enrollment(models.Model):
    """ A participant in a split testing experiment """
    user = models.ForeignKey(
        getattr(settings, 'AUTH_USER_MODEL', 'auth.User'), null=True)
    experiment = models.ForeignKey(Experiment)
    enrollment_date = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(null=True)
    alternative = models.CharField(max_length=50)

    class Meta:
        unique_together = ('user', 'experiment')

    def __unicode__(self):
        return u'%s - %s' % (self.user, self.experiment)

    def to_dict(self):
        data = {
            'user': self.user,
            'experiment': self.experiment,
            'enrollment_date': self.enrollment_date,
            'alternative': self.alternative,
            'goals': self.goals,
        }
        return data


def weighted_choice(choices):
    total = sum(w for c, w in choices)
    r = random.uniform(0, total)
    upto = 0
    for c, w in choices:
        upto += w
        if upto >= r:
            return c
