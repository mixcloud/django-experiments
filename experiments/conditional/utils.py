# coding=utf-8
from lxml import etree


def xml_bool(xml_str):
    xml_tree = etree.XML(xml_str)
    return _parse_recursive(xml_tree)


def _parse_recursive(elem):
    if elem.tag.lower() == 'true':
        return True
    if elem.tag.lower() == 'false':
        return False
    if elem.tag.lower() == 'any_of':
        return any(map(_parse_recursive, elem.getchildren()))
    if elem.tag.lower() == 'all_of':
        children = elem.getchildren()
        if len(children) == 0:
            # # We don't want this:
            # >>> all([])
            # True
            return False
        return all(map(_parse_recursive, children))
    raise ValueError('unknown tag: {}'.format(elem))


class Experiments(object):
    """
    Helper for conditional experiments, meant to be added to request object
    """

    def __init__(self, context):
        from ..models import Experiment
        self.request = context['request']
        self.context = context
        self.report = {
            'auto_enroll': {},
        }
        self.instances = Experiment.objects.filter(auto_enroll=True)

    def get_participant(self):
        """
        Returns an instance of experiments.utile.WebUser or its subclass
        Cached on the request.
        """
        from ..utils import participant
        return participant(self.request)

    def conditionally_enroll(self):
        """
        Enroll current user in all experiments that are marked with
        `auto_enroll` and evaluate at least one of the conditionals
        positively.
        """
        for i in self.instances:
            active = i.should_auto_enroll(self.request)
            if active:
                variate = self.get_participant().enroll(
                    i.name, i.alternative_keys)
            else:
                variate = self.get_participant().get_alternative(i.name)
            self._report(i, active, variate)

    def _report(self, instance, active, variate):
        """
        Populate self.report dict, used to set cookie with
        experiments data. The cookie is useful for debugging
        and verifying whether an experiment is running.
        """
        self.report['auto_enroll'][instance.name] = {
            'auto-enrolling': active,
            'enrolled_variate': variate,
        }
