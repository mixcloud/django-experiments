from experiments import counters, conf
import logging
import json

PARTICIPANT_KEY = '%s:%s:participant'
GOAL_KEY = '%s:%s:%s:goal'

logger = logging.getLogger('experiments')

class ExperimentCounter(object):
    def __init__(self):
        self.counters = counters.Counters()

    def increment_participant_count(self, experiment, alternative_name, participant_identifier):
        counter_key = PARTICIPANT_KEY % (experiment.name, alternative_name)
        self.counters.increment(counter_key, participant_identifier)
        logger.info(json.dumps({'type':'participant_add', 'experiment': experiment.name, 'alternative': alternative_name, 'participant': participant_identifier}))

    def increment_goal_count(self, experiment, alternative_name, goal_name, participant_identifier, count=1):
        counter_key = GOAL_KEY % (experiment.name, alternative_name, goal_name)
        self.counters.increment(counter_key, participant_identifier, count)
        logger.info(json.dumps({'type':'goal_hit', 'goal': goal_name, 'goal_count': count, 'experiment': experiment.name, 'alternative': alternative_name, 'participant': participant_identifier}))

    def remove_participant(self, experiment, alternative_name, participant_identifier):
        counter_key = PARTICIPANT_KEY % (experiment.name, alternative_name)
        self.counters.clear(counter_key, participant_identifier)
        logger.info(json.dumps({'type':'participant_remove', 'experiment': experiment.name, 'alternative': alternative_name, 'participant': participant_identifier}))

        # Remove goal records
        for goal_name in conf.ALL_GOALS:
            counter_key = GOAL_KEY % (experiment.name, alternative_name, goal_name)
            self.counters.clear(counter_key, participant_identifier)

    def participant_count(self, experiment, alternative):
        return self.counters.get(PARTICIPANT_KEY % (experiment.name, alternative))

    def goal_count(self, experiment, alternative, goal):
        return self.counters.get(GOAL_KEY % (experiment.name, alternative, goal))

    def participant_goal_frequencies(self, experiment, alternative, participant_identifier):
        for goal in conf.ALL_GOALS:
            yield goal, self.counters.get_frequency(GOAL_KEY % (experiment.name, alternative, goal), participant_identifier)

    def goal_distribution(self, experiment, alternative, goal):
        return self.counters.get_frequencies(GOAL_KEY % (experiment.name, alternative, goal))

    def delete(self, experiment):
        self.counters.reset_pattern(experiment.name + "*")
