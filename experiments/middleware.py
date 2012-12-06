from experiments import record_goal

class ExperimentsMiddleware(object):
    def process_response(self, request, response):
        experiments_goal = request.COOKIES.get('experiments_goal', None)
        if experiments_goal:
            for goal in experiments_goal.split('%20'): # multiple goals separated by space
                record_goal(goal, request)
            response.delete_cookie('experiments_goal')
        return response
