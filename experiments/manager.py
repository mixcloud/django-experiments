from django.conf import settings

from models import ExperimentManager, Experiment

experiment_manager = ExperimentManager(Experiment, key='name', value='value', instances=True, auto_create=getattr(settings, 'EXPERIMENTS_AUTO_CREATE', True))