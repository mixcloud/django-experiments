# coding=utf-8
from django.conf import settings
from itertools import chain
import re

CONTROL_GROUP = 'control'

VISIT_PRESENT_COUNT_GOAL = '_retention_present_visits'
VISIT_NOT_PRESENT_COUNT_GOAL = '_retention_not_present_visits'

BUILT_IN_GOALS = (
    VISIT_PRESENT_COUNT_GOAL,
    VISIT_NOT_PRESENT_COUNT_GOAL,
)

SESSION_LENGTH = getattr(settings, 'EXPERIMENTS_SESSION_LENGTH', 6)

USER_GOALS = getattr(settings, 'EXPERIMENTS_GOALS', [])
ALL_GOALS = tuple(chain(USER_GOALS, BUILT_IN_GOALS))

VERIFY_HUMAN = getattr(settings, 'EXPERIMENTS_VERIFY_HUMAN', True)

CONFIRM_HUMAN = getattr(settings, 'EXPERIMENTS_CONFIRM_HUMAN', True)

CONFIRM_HUMAN_SESSION_KEY = getattr(settings, 'EXPERIMENTS_CONFIRM_HUMAN_SESSION_KEY', 'experiments_verified_human')

DISABLED_EXPERIMENTS_SESSION_KEY = getattr(settings, 'EXPERIMENTS_DISABLED_EXPERIMENTS_SESSION_KEY', 'experiments_disabled')

BOT_REGEX = re.compile("(Baidu|Gigabot|Googlebot|YandexBot|AhrefsBot|TVersity|libwww-perl|Yeti|lwp-trivial|msnbot|bingbot|facebookexternalhit|Twitterbot|Twitmunin|SiteUptime|TwitterFeed|Slurp|WordPress|ZIBB|ZyBorg)", re.IGNORECASE)


API = {
    'api_mode': '',
    'remotes': [],
    'local': {
        'name': 'Local',
        'page_size': 100,
    }
}
project_settings = getattr(settings, 'EXPERIMENTS_API', {'local': {}})
API['local'].update(project_settings['local'])
project_settings['local'] = API['local']
API.update(project_settings)
