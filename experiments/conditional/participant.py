# coding=utf-8
from .. import utils


SESSION_KEY = 'conditional_experiments_report'


class ConditionalParticipantProxy(object):

    def __init__(self, participant):
        self.participant = participant
        self.session = getattr(participant.request, 'session', None)

    def save_report(self, report):
        # caveat: this needs sessions to work
        if self.session is not None:
            self.session[SESSION_KEY] = report

    def get_report(self):
        if self.session is None:
            return None
        return self.session.get(SESSION_KEY)

    def _get_negatives(self):
        report = self.get_report()
        negatives = set()
        for name, data in report['auto_enroll'].items():
            if not data['auto-enrolling']:
                negatives.add(name)

    def _get_all_enrollments(self):
        enrollments = self.participant._get_all_enrollments()
        negatives = self._get_negatives()
        for enrollment in enrollments:
            if enrollment.experiment not in negatives:
                yield enrollment

    def __getattr__(self, item):
        return getattr(self.participant, item)


unconditional_participant = utils.participant


def participant(request):
    return ConditionalParticipantProxy(unconditional_participant(request))


utils.participant = participant
