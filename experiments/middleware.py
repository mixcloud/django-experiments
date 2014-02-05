from experiments import record_goal

from django.middleware.csrf import get_token

from urllib import unquote

class ExperimentsMiddleware(object):
    def process_response(self, request, response):
        experiments_goal = request.COOKIES.get('experiments_goal', None)
        if experiments_goal:
            for goal in unquote(experiments_goal).split(' '): # multiple goals separated by space
                record_goal(goal, request)
            response.delete_cookie('experiments_goal')
        return response

    def process_request(self, request):
        """
        Allows setting of experiment and alternative via URL Params.
        """
        experiment = request.GET.get('exp', '')
        alternative = request.GET.get('alt', 'control')
        if experiment is not '':
            request.session['experiment'] = experiment
            request.session['alternative'] = alternative
        return None

class CSRFMiddleware(object):
    def process_request(self, request):
        # Forces process_response to set the CSRF cookie for POSTing
        # experiment goals to server.
        get_token(request)
        return None
