from experiments.utils import participant

class ExperimentsRetentionMiddleware(object):
    def process_response(self, request, response):
        # Don't track, failed pages, ajax requests, logged out users or widget impressions.
        # We detect widgets by relying on the fact that they are flagged as being embedable
        if response.status_code != 200 or request.is_ajax() or getattr(response, 'xframe_options_exempt', False):
            return response

        experiment_user = participant(request)
        experiment_user.visit()

        return response