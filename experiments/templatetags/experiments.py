from __future__ import absolute_import

from django import template
from django.core.urlresolvers import reverse

from experiments.utils import participant
from uuid import uuid4

register = template.Library()

@register.inclusion_tag('experiments/goal.html')
def experiment_goal(goal_name):
    return { 'url': reverse('experiment_goal', kwargs={'goal_name': goal_name, 'cache_buster': uuid4()}) }

class ExperimentNode(template.Node):
    def __init__(self, node_list, experiment_name, alternative):
        self.node_list = node_list
        self.experiment_name = experiment_name
        self.alternative = alternative

    def render(self, context):
        # Get User object
        request = context.get('request', None)

        if request and hasattr(request, 'experiment_user'):
            user = request.experiment_user
        else:
            user = participant(request)

        # Should we render?
        if user.is_enrolled(self.experiment_name, self.alternative, request):
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
