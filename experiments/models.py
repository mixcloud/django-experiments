from django.db import models
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings

import random
import json
try:
    from django.db.models import JSONField
except ImportError:  # Django < 3.1
    from jsonfield import JSONField

from experiments.counters import Counters
from experiments.dateutils import now
from experiments import conf


CONTROL_STATE = 0
ENABLED_STATE = 1
TRACK_STATE = 3

STATES = (
    (CONTROL_STATE, 'Default/Control'),
    (ENABLED_STATE, 'Enabled'),
    (TRACK_STATE, 'Track'),
)


class Experiment(models.Model):
    name = models.CharField(primary_key=True, max_length=128)
    description = models.TextField(default="", blank=True, null=True)
    alternatives = JSONField(default=dict, blank=True)
    relevant_chi2_goals = models.TextField(default="", null=True, blank=True)
    relevant_mwu_goals = models.TextField(default="", null=True, blank=True)

    state = models.IntegerField(default=CONTROL_STATE, choices=STATES)

    start_date = models.DateTimeField(default=now, blank=True, null=True, db_index=True)
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
            return random.choice(list(self.alternatives))

    def __unicode__(self):
        return self.name

    def to_dict(self):
        data = {
            'name': self.name,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'state': self.state,
            'description': self.description,
            'relevant_chi2_goals': self.relevant_chi2_goals,
            'relevant_mwu_goals': self.relevant_mwu_goals,
            'default_alternative': self.default_alternative,
            'alternatives': ','.join(self.alternatives.keys()),
        }
        return data

    def to_dict_serialized(self):
        return json.dumps(self.to_dict(), cls=DjangoJSONEncoder)
    
    def reset_counters(self):
        Counters().reset_prefix(self.name)
    
    def delete(self, reset_counters=True, *args, **kwargs):
        if reset_counters:
            self.reset_counters()
        return super(Experiment, self).delete(*args, **kwargs)



class Enrollment(models.Model):
    """ A participant in a split testing experiment """
    user = models.ForeignKey(getattr(settings, 'AUTH_USER_MODEL', 'auth.User'), on_delete=models.CASCADE, null=True)
    session_key = models.CharField(max_length=40, null=True)
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE)
    enrollment_date = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(null=True)
    alternative = models.CharField(max_length=50)

    def clean(self):
        if self.user_id and self.session_key:
            raise ValidationError("Only one of user_id or session_key can be set")
        elif not self.user_id and not self.session_key:
            raise ValidationError("Must set a user_id or session_key")

    class Meta:
        unique_together = (('user', 'experiment'), ('session_key', 'experiment'))

    def __unicode__(self):
        if self.user_id:
            return u'%s - %s' % (self.user, self.experiment)
        else:
            return u'%s - %s' % (self.session_key, self.experiment)


def weighted_choice(choices):
    total = sum(w for c, w in choices)
    r = random.uniform(0, total)
    upto = 0
    for c, w in choices:
        upto += w
        if upto >= r:
            return c
