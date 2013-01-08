import random

from experiments.models import Experiment
from experiments.utils import record_goal, WebUser

class ExperimentsMiddleware(object):
    def process_response(self, request, response):
        experiments_goal = request.COOKIES.get('experiments_goal', None)
        if experiments_goal:
            record_goal(request, experiments_goal)
            response.delete_cookie('experiments_goal')
        return response

    def process_request(self, request):
        """
        Allows setting of experiment and alternative via URL Params.
        """
        experiment = request.GET.get('exp', '')
        alternative = request.GET.get('alt', '')
        if experiment is not '' and alternative is not '':
            request.session['experiment'] = experiment
            request.session['alternative'] = alternative
        return None
