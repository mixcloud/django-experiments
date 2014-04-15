from django.conf import settings
from experiments.models import Experiment
from modeldict import ModelDict

experiment_manager = ModelDict(Experiment, key='name', value='value', instances=True, auto_create=getattr(settings, 'EXPERIMENTS_AUTO_CREATE', True))
