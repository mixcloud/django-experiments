# coding=utf-8

try:
    # for Django >= 1.10
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    # for Django < 1.10
    MiddlewareMixin = object


class ExperimentsRetentionMiddleware(MiddlewareMixin):

    def process_response(self, request, response):
        # Don't track, failed pages, ajax requests, logged out users or widget impressions.
        # We detect widgets by relying on the fact that they are flagged as being embedable
        from experiments.utils import participant

        if response.status_code != 200 or request.is_ajax() or getattr(response, 'xframe_options_exempt', False):
            return response

        experiment_user = participant(request)
        experiment_user.visit()

        return response


class ConfirmHumanMiddleware(MiddlewareMixin):

    def process_request(self, request):
        from experiments.utils import participant

        participant(request).confirm_human()
