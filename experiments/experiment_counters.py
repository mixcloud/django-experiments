class ExperimentCounter(object):
    def increment_participant_count(self, experiment, alternative_name, participant_identifier):
        return experiment.increment_participant_count(alternative_name, participant_identifier)

    def increment_goal_count(self, experiment, alternative_name, goal_name, participant_identifier, count=1):
        return experiment.increment_goal_count(alternative_name, goal_name, participant_identifier, count)

    def remove_participant(self, experiment, alternative_name, participant_identifier):
        return experiment.remove_participant(alternative_name, participant_identifier)

    def participant_count(self, experiment, alternative):
        return experiment.participant_count(alternative)

    def goal_count(self, experiment, alternative, goal):
        return experiment.goal_count(alternative, goal)

    def participant_goal_frequencies(self, experiment, alternative, participant_identifier):
        return experiment.participant_goal_frequencies(alternative, participant_identifier)

    def goal_distribution(self, experiment, alternative, goal):
        return experiment.goal_distribution(alternative, goal)

    def delete(self, experiment):
        return experiment.delete()
