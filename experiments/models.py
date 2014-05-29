from django.core.urlresolvers import reverse
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings

from jsonfield import JSONField

from gargoyle.manager import gargoyle
from gargoyle.models import Switch

import random
import json

from experiments import conf
from experiments.dateutils import now


CONTROL_STATE = 0
ENABLED_STATE = 1
GARGOYLE_STATE = 2
TRACK_STATE = 3

STATES = (
    (CONTROL_STATE, 'Control'),
    (ENABLED_STATE, 'Enabled'),
    (GARGOYLE_STATE, 'Gargoyle'),
    (TRACK_STATE, 'Track'),
)


class Experiment(models.Model):
    name = models.CharField(primary_key=True, max_length=128)
    description = models.TextField(default="", blank=True, null=True)
    alternatives = JSONField(default={}, blank=True)
    relevant_chi2_goals = models.TextField(default="", null=True, blank=True)
    relevant_mwu_goals = models.TextField(default="", null=True, blank=True)
    switch_key = models.CharField(default="", max_length=50, null=True, blank=True)

    state = models.IntegerField(default=CONTROL_STATE, choices=STATES)

    start_date = models.DateTimeField(default=now, blank=True, null=True, db_index=True)
    end_date = models.DateTimeField(blank=True, null=True)

    def is_displaying_alternatives(self):
        if self.state == CONTROL_STATE:
            return False
        elif self.state == ENABLED_STATE:
            return True
        elif self.state == GARGOYLE_STATE:
            return True
        elif self.state == TRACK_STATE:
            return True
        else:
            raise Exception("Invalid experiment state %s!" % self.state)

    def is_accepting_new_users(self, request):
        if self.state == CONTROL_STATE:
            return False
        elif self.state == ENABLED_STATE:
            return True
        elif self.state == GARGOYLE_STATE:
            return gargoyle.is_active(self.switch_key, request)
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

    def random_alternative(self):
        if all('weight' in alt for alt in self.alternatives.values()):
            return weighted_choice([(name, details['weight']) for name, details in self.alternatives.items()])
        else:
            return random.choice(self.alternatives.keys())

    def __unicode__(self):
        return self.name

    def to_dict(self):
        data = {
            'name': self.name,
            'edit_url': reverse('experiments:results', kwargs={'name': self.name}),
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
        # Create new switch
        if self.switch_key and conf.SWITCH_AUTO_CREATE:
            try:
                Switch.objects.get(key=self.switch_key)
            except Switch.DoesNotExist:
                Switch.objects.create(key=self.switch_key, label=conf.SWITCH_LABEL % self.name, description=self.description)

        if not self.switch_key and self.state == 2:
            self.state = 0

        super(Experiment, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Delete existing switch
        if conf.SWITCH_AUTO_DELETE:
            try:
                Switch.objects.get(key=Experiment.objects.get(name=self.name).switch_key).delete()
            except Switch.DoesNotExist:
                pass

        super(Experiment, self).delete(*args, **kwargs)


class Enrollment(models.Model):
    """ A participant in a split testing experiment """
    user = models.ForeignKey(getattr(settings, 'AUTH_USER_MODEL', 'auth.User'), null=True)
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


