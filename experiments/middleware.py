from django.conf import settings
from importlib import import_module

from experiments.utils import participant

try:
    # for Django >= 1.10
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    # for Django < 1.10
    MiddlewareMixin = object

class ExperimentsRetentionMiddleware(MiddlewareMixin):

    # should we create session in process_request ?

    def process_response(self, request, response):
        # Don't track, failed pages, ajax requests, logged out users or widget impressions.
        # We detect widgets by relying on the fact that they are flagged as being embedable
        if response.status_code != 200 or request.is_ajax() or getattr(response, 'xframe_options_exempt', False):
            return response

        # create session if not exists     see http://stackoverflow.com/a/5131421/127114
        engine = import_module(settings.SESSION_ENGINE)
        session_key = request.COOKIES.get(settings.SESSION_COOKIE_NAME, None)
        request.session = engine.SessionStore(session_key)
        if not request.session.exists(request.session.session_key):
            request.session.create()


        experiment_user = participant(request)
        experiment_user.visit()

        return response
