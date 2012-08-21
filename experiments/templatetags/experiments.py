from __future__ import absolute_import

from django import template

from experiments.models import Experiment
from experiments.manager import experiment_manager
from experiments.utils import StaticUser, WebUser
import random

register = template.Library()

@register.inclusion_tag('experiments/goal.html')
def experiment_goal(goal_name):
    return { 'goal_name': goal_name, 'random_number': random.randint(1,1000000) }

class ExperimentNode(template.Node):
    def __init__(self, node_list, experiment_name, alternative):
        self.node_list = node_list
        self.experiment_name = experiment_name
        self.alternative = alternative

    def render(self, context):
        # Get User object
        request = context.get('request', None)

        if request is None:
            user = StaticUser()
        else:
            # Create experiment_user in session if not already
            if not hasattr(request, 'experiment_user'):
                request.experiment_user = WebUser(request)
            user = request.experiment_user

        # Should we render?
        if Experiment.show_alternative(self.experiment_name, user, self.alternative, experiment_manager):
            response = self.node_list.render(context)
        else:
            response = ""

        return response

@register.tag('experiment')
def experiment(parser, token):
    """
    Split Testing experiment tag has the following syntax :
    
    {% experiment <experiment_name> <alternative>  %}
    experiment content goes here
    {% endexperiment %}
    
    If the alternative name is neither 'test' nor 'control' an exception is raised
    during rendering.
    """
    try:
        tag_name, experiment_name, alternative = token.split_contents()
        node_list = parser.parse(('endexperiment', ))
        parser.delete_first_token()
    except ValueError:
        raise template.TemplateSyntaxError("Syntax should be like :"
                "{% experiment experiment_name alternative %}")
    
    return ExperimentNode(node_list, experiment_name, alternative)