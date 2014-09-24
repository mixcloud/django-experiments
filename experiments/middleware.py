from experiments.utils import participant

class ExperimentsRetentionMiddleware(object):
    def process_response(self, request, response):
        #  We detect widgets by relying on the fact that they are flagged as being embedable, and don't include these in visit tracking
        if getattr(response, 'xframe_options_exempt', False):
            return response

        experiment_user = participant(request)
        experiment_user.visit()

        return response