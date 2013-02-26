from __future__ import absolute_import
from json import dumps as to_json

from django import template
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe

from experiments.utils import participant
from experiments.manager import experiment_manager
from uuid import uuid4

register = template.Library()

@register.inclusion_tag('experiments/goal.html')
def experiment_goal(goal_name):
    return { 'url': reverse('experiment_goal', kwargs={'goal_name': goal_name, 'cache_buster': uuid4()}) }

class ExperimentNode(template.Node):
    def __init__(self, node_list, experiment_name, alternative, user_variable):
        self.node_list = node_list
        self.experiment_name = experiment_name
        self.alternative = alternative
        self.user_variable = user_variable

    def render(self, context):
        # Get User object
        if self.user_variable:
            auth_user = self.user_variable.resolve(context)
            user = participant(user=auth_user)
            gargoyle_key = auth_user
        else:
            request = context.get('request', None)
            user = participant(request)
            gargoyle_key = request

        # Should we render?
        if user.is_enrolled(self.experiment_name, self.alternative, gargoyle_key):
            response = self.node_list.render(context)
        else:
            response = ""

        return response

def _parse_token_contents(token_contents):
    (_, experiment_name, alternative), remaining_tokens = token_contents[:3], token_contents[3:]
    weight = None
    user_variable = None

    for offset, token in enumerate(remaining_tokens):
        if '=' in token:
            name, expression = token.split('=', 1)
            if name == 'weight':
                weight = expression
            elif name == 'user':
                user_variable = template.Variable(expression)
            else:
                raise ValueError()
        elif offset == 0:
            # Backwards compatibility, weight as positional argument
            weight = token
        else:
            raise ValueError()

    return experiment_name, alternative, weight, user_variable


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
        token_contents = token.split_contents()
        experiment_name, alternative, weight, user_variable = _parse_token_contents(token_contents)

        node_list = parser.parse(('endexperiment', ))
        parser.delete_first_token()
    except ValueError:
        raise template.TemplateSyntaxError("Syntax should be like :"
                "{% experiment experiment_name alternative [weight=val] [user=val] %}")

    experiment = experiment_manager.get(experiment_name, None)
    if experiment:
        experiment.ensure_alternative_exists(alternative, weight)

    return ExperimentNode(node_list, experiment_name, alternative, user_variable)

@register.simple_tag(takes_context=True)
def visit(context):
    request = context.get('request', None)
    participant(request).visit()
    return ""

@register.inclusion_tag('experiments/enrollments.html', takes_context=True)
def enrollments(context):
    """
    Adds an array named 'enrollments' to the experiments javascript
    variable.  This array of name, alternative object literals describes
    each running experiment and the alternative selected for the user.
    Other template tags may select experiments and alternatives so use this
    tag after all of the other experiments template tags in your template.
    """
    request = context.get('request', None)
    user = participant(request)
    enrollments = [{'experiment': enrollment.experiment.name,
                    'alternative': enrollment.alternative}
                    for enrollment in user._get_all_enrollments()]
    return {'experiment_enrollments': mark_safe(to_json(enrollments))}
