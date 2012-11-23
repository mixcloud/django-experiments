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
        if experiment is not '':
            try:
                exp = Experiment.objects.get(name=experiment)
                user = WebUser(request)

                # If user is not enrolled, set experiment and alternative.
                if user.get_enrollment(exp) is None:
                    if (alternative is not '' 
                            and alternative in exp.alternatives):
                        user.set_enrollment(exp, alternative)
                    else:
                        user.set_enrollment(exp,
                                    random.choice(exp.alternatives.keys()))
            except Experiment.DoesNotExist:
                return None
        return None
