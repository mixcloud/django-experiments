from experiments.utils import participant

try:
    # for Django >= 1.10
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    # for Django < 1.10
    MiddlewareMixin = object


def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


class ExperimentsRetentionMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # Don't track, failed pages, ajax requests, logged out users or widget impressions.
        # We detect widgets by relying on the fact that they are flagged as being embedable
        if response.status_code != 200 or is_ajax(request) or getattr(response, 'xframe_options_exempt', False):
            return response

        experiment_user = participant(request)
        experiment_user.visit()

        # record cookie goal
        goal_name = request.COOKIES.get('experiments_goal')
        participant(request).goal(goal_name)

        return response
