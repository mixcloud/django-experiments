from __future__ import absolute_import

from .stats import StatsTestCase
from .mannwhitney import MannWhitneyTestCase
from .counter import CounterTestCase
from .webuser import WebUserAnonymousTestCase, WebUserAuthenticatedTestCase, BotTestCase
from .templatetags import ExperimentTemplateTagTestCase
from .signals import SignalsTestCase
from . import webuser_incorporate


def load_tests(*args, **kwargs):
    return webuser_incorporate.load_tests(*args, **kwargs)
