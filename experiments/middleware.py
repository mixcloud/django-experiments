from experiments import record_goal

from urllib import unquote

class ExperimentsMiddleware(object):
    def process_response(self, request, response):
        experiments_goal = request.COOKIES.get('experiments_goal', None)
        if experiments_goal:
            for goal in unquote(experiments_goal).split(' '): # multiple goals separated by space
                record_goal(goal, request)
            response.delete_cookie('experiments_goal')
        return response
