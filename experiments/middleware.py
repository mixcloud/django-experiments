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
        experiment = request.GET.get('bucket', '')
        if experiment is not '':
            try:
                exp = Experiment.objects.get(name=experiment)
                user = WebUser(request)
                if user.get_enrollment(exp) is None:
                    user.set_enrollment(exp, random.choice(exp.alternatives.keys()))
            except Experiment.DoesNotExist:
                pass
        return None
