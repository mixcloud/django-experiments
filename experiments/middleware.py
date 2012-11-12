from experiments import record_goal

class ExperimentsMiddleware(object):
    def process_response(self, request, response):
        experiments_goal = request.COOKIES.get('experiments_goal', None)
        if experiments_goal:
            record_goal(experiments_goal, request)
            response.delete_cookie('experiments_goal')
        return response
