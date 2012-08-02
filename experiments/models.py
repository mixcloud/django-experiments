from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.utils import simplejson     
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings

from jsonfield import JSONField
from modeldict import ModelDict

from gargoyle.manager import gargoyle
from gargoyle.models import Switch

import datetime

import random

CONTROL_GROUP = 'control'

CONTROL_STATE = 0
ENABLED_STATE = 1
GARGOYLE_STATE = 2

STATES = (
    (CONTROL_STATE, 'Control'),
    (ENABLED_STATE, 'Enabled'),
    (GARGOYLE_STATE, 'Gargoyle'),
)

class Experiment(models.Model):
    name = models.CharField(primary_key=True, max_length=128)
    description = models.TextField(default="", blank=True, null=True)
    alternatives = JSONField(default="{}", blank=True)
    relevant_goals = models.TextField(default = "", null=True, blank=True)
    switch_key = models.CharField(default = "", max_length=50, null=True, blank=True)

    state = models.IntegerField(default=CONTROL_STATE, choices=STATES)

    start_date = models.DateTimeField(default=datetime.datetime.now, blank=True, null=True, db_index=True)
    end_date = models.DateTimeField(blank=True, null=True)

    def __unicode__(self):
        return self.name

    @classmethod
    def show_alternative(self, experiment_name, experiment_user, alternative, experiment_manager):
        """ does the real work """
        try:
            experiment = experiment_manager[experiment_name] # use cache where possible
        except KeyError:
            return alternative == CONTROL_GROUP

        if experiment.state == CONTROL_STATE:
            return alternative == CONTROL_GROUP

        if experiment.state == GARGOYLE_STATE:
            if not gargoyle.is_active(experiment.switch_key, experiment_user.request):
                return alternative == CONTROL_GROUP                

        if experiment.state != ENABLED_STATE and experiment.state != GARGOYLE_STATE:
            raise Exception("Invalid experiment state %s!" % experiment.state)

        # Add new alternatives to experiment model
        if alternative not in experiment.alternatives:
            experiment.alternatives[alternative] = {}
            experiment.alternatives[alternative]['enabled'] = True
            experiment.save()

        # Lookup User alternative
        assigned_alternative = experiment_user.get_enrollment(experiment)

        # No alternative so assign one
        if assigned_alternative is None:
            assigned_alternative = random.choice(experiment.alternatives.keys())
            experiment_user.set_enrollment(experiment, assigned_alternative)

        return alternative == assigned_alternative

    def to_dict(self):
        data = {
            'name': self.name,
            'edit_url': reverse('experiments:results', kwargs={'name': self.name}),
            'start_date': self.start_date,
            'end_date': self.end_date,
            'state': self.state,
            'switch_key': self.switch_key,
            'description': self.description,
            'relevant_goals': self.relevant_goals,
        }
        return data

    def to_dict_serialized(self):
        return simplejson.dumps(self.to_dict(), cls=DjangoJSONEncoder)

    def save(self, *args, **kwargs):
        # Delete existing switch
        if getattr(settings, 'EXPERIMENTS_SWITCH_AUTO_DELETE', True):
            try:
                Switch.objects.get(key=Experiment.objects.get(name=self.name).switch_key).delete()
            except (Switch.DoesNotExist, Experiment.DoesNotExist):
                pass

        # Create new switch
        if self.switch_key and getattr(settings, 'EXPERIMENTS_SWITCH_AUTO_CREATE', True):
            try:
                Switch.objects.get(key=self.switch_key)
            except Switch.DoesNotExist:
                Switch.objects.create(key=self.switch_key, label=getattr(settings, 'EXPERIMENTS_SWITCH_LABEL', "Experiment: %s") % self.name, description=self.description)

        if not self.switch_key and self.state == 2:
            self.state = 0

        super(Experiment, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Delete existing switch
        if getattr(settings, 'EXPERIMENTS_SWITCH_AUTO_DELETE', True):
            try:
                Switch.objects.get(key=Experiment.objects.get(name=self.name).switch_key).delete()
            except Switch.DoesNotExist:
                pass

        super(Experiment, self).delete(*args, **kwargs)



class ExperimentManager(ModelDict):
    def __init__(self, *args, **kwargs):
        self._registry = {}
        super(ExperimentManager, self).__init__(*args, **kwargs)

    def __getitem__(self, key):
        experiment = super(ExperimentManager, self).__getitem__(key)
        return experiment

class Enrollment(models.Model):
    """ A participant in a split testing experiment """
    user = models.ForeignKey(User, null=True)
    experiment = models.ForeignKey(Experiment)
    enrollment_date = models.DateField(db_index=True, auto_now_add=True)
    alternative = models.CharField(max_length=50)
    goals = JSONField(default="[]", blank=True)

    class Meta:
        unique_together = ('user', 'experiment')

    def to_dict(self):
        data = {
            'user': self.user,
            'experiment': self.experiment,
            'enrollment_date': self.enrollment_date,
            'alternative': self.alternative,
            'goals': self.goals,
        }
        return data