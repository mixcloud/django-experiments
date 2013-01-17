from django.conf import settings
from itertools import chain
import re

CONTROL_GROUP = 'control'

VISIT_COUNT_GOAL = '_retention_visits'

BUILT_IN_GOALS = (
    VISIT_COUNT_GOAL,
)

USER_GOALS = getattr(settings, 'EXPERIMENTS_GOALS', [])
ALL_GOALS = tuple(chain(USER_GOALS, BUILT_IN_GOALS))

DO_NOT_AGGREGATE_GOALS = (
    VISIT_COUNT_GOAL,
)

VERIFY_HUMAN = getattr(settings, 'EXPERIMENTS_VERIFY_HUMAN', True)

SWITCH_AUTO_CREATE = getattr(settings, 'EXPERIMENTS_SWITCH_AUTO_CREATE', True)
SWITCH_LABEL = getattr(settings, 'EXPERIMENTS_SWITCH_LABEL', "Experiment: %s")
SWITCH_AUTO_DELETE = getattr(settings, 'EXPERIMENTS_SWITCH_AUTO_DELETE', True)

BOT_REGEX = re.compile("(Baidu|Gigabot|Googlebot|YandexBot|AhrefsBot|TVersity|libwww-perl|Yeti|lwp-trivial|msnbot|bingbot|facebookexternalhit|Twitterbot|Twitmunin|SiteUptime|TwitterFeed|Slurp|WordPress|ZIBB|ZyBorg)", re.IGNORECASE)
