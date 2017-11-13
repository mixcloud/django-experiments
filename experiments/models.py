# coding=utf-8
import random
import json
import logging

from django.core.validators import MaxValueValidator
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings
from django.utils.encoding import python_2_unicode_compatible

from experiments import conf
from experiments.dateutils import now
from experiments.conditional.models import ConditionalMixin
from jsonfield import JSONField


logger = logging.getLogger(__file__)


CONTROL_STATE = 0
ENABLED_STATE = 1
TRACK_STATE = 3

STATES = (
    (CONTROL_STATE, 'Default/Control'),
    (ENABLED_STATE, 'Enabled'),
    (TRACK_STATE, 'Track'),
)


@python_2_unicode_compatible
class Experiment(ConditionalMixin, models.Model):
    name = models.CharField(
        primary_key=True,
        max_length=128,
        help_text='This field is the primary key and is only editable'
                  ' when creating the experiment',
    )
    description = models.TextField(default="", blank=True, null=True)
    alternatives = JSONField(default={}, blank=True, null=False)
    relevant_chi2_goals = models.TextField(default="", null=True, blank=True)
    relevant_mwu_goals = models.TextField(default="", null=True, blank=True)
    state = models.IntegerField(default=CONTROL_STATE, choices=STATES)
    start_date = models.DateTimeField(
        default=now, blank=True, null=True, db_index=True)
    end_date = models.DateTimeField(blank=True, null=True)

    def is_displaying_alternatives(self):
        if self.state == CONTROL_STATE:
            return False
        elif self.state == ENABLED_STATE:
            return True
        elif self.state == TRACK_STATE:
            return True
        else:
            raise Exception("Invalid experiment state %s!" % self.state)

    def is_accepting_new_users(self):
        if self.state == CONTROL_STATE:
            return False
        elif self.state == ENABLED_STATE:
            return True
        elif self.state == TRACK_STATE:
            return False
        else:
            raise Exception("Invalid experiment state %s!" % self.state)

    def ensure_alternative_exists(self, alternative, weight=None):
        if alternative not in self.alternatives:
            self.alternatives[alternative] = {}
            self.alternatives[alternative]['enabled'] = True
            self.save()
        if weight is not None and 'weight' not in self.alternatives[alternative]:
            self.alternatives[alternative]['weight'] = float(weight)
            self.save()

    @property
    def default_alternative(self):
        for alternative, alternative_conf in self.alternatives.items():
            if alternative_conf.get('default'):
                return alternative
        return conf.CONTROL_GROUP

    def set_default_alternative(self, alternative):
        for alternative_name, alternative_conf in self.alternatives.items():
            if alternative_name == alternative:
                alternative_conf['default'] = True
            elif 'default' in alternative_conf:
                del alternative_conf['default']

    def random_alternative(self):
        if all('weight' in alt for alt in self.alternatives.values()):
            return weighted_choice([(name, details['weight']) for name, details in self.alternatives.items()])
        else:
            if any('weight' in alt for alt in self.alternatives.values()):
                logger.warning(
                    'Ignoring weights for experiment {}, all alternatives'
                    ' need to have specified weights.'.format(
                        self.name,
                    ))
            return random.choice(list(self.alternatives))

    @property
    def alternative_keys(self):
        return list(self.alternatives.keys())

    @property
    def has_alternatives(self):
        """
        When an experiment is created it only has 'control' alternative,
        until an `enroll` command (template tag or WebUser.enroll() method)
        is first called.

        Note: PUMA-83 will need to introduce some changes to this behaviour
        """
        return len(self.alternative_keys) > 1

    def __str__(self):
        return self.name

    def to_dict(self):
        data = {
            'name': self.name,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'state': self.state,
            'auto_enroll': self.auto_enroll,
            'description': self.description,
            'relevant_chi2_goals': self.relevant_chi2_goals,
            'relevant_mwu_goals': self.relevant_mwu_goals,
            'default_alternative': self.default_alternative,
            'alternatives': ','.join(self.alternative_keys),
        }
        return data

    def to_dict_serialized(self):
        return json.dumps(self.to_dict(), cls=DjangoJSONEncoder)


@python_2_unicode_compatible
class ExperimentAlternative(models.Model):
    experiment = models.ForeignKey(Experiment)
    name = models.CharField(max_length=254, blank=False, null=False)
    weight = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(100)],
        null=True,
        blank=True,
        default=None,
    )

    class Meta:
        ordering = ('name',)

    def __str__(self):
        if self.weight:
            return '{} ({})'.format(self.name, self.weight)
        return self.name

    def to_dict(self):
        representation = {
            'enabled': True,
        }
        if self.weight is not None:
            representation.update(weight=self.weight)
        return representation


@python_2_unicode_compatible
class Enrollment(models.Model):
    """ A participant in a split testing experiment """
    user = models.ForeignKey(getattr(settings, 'AUTH_USER_MODEL', 'auth.User'))
    experiment = models.ForeignKey(Experiment)
    enrollment_date = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(null=True)
    alternative = models.CharField(max_length=50)

    class Meta:
        unique_together = ('user', 'experiment')

    def __str__(self):
        return u'%s - %s' % (self.user, self.experiment)


def weighted_choice(choices):
    total = sum(w for c, w in choices)
    r = random.uniform(0, total)
    upto = 0
    for c, w in choices:
        upto += w
        if upto >= r:
            return c
