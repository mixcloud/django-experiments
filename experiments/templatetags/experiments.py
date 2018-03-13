from __future__ import absolute_import

from django import template
from django.urls import reverse

from experiments.utils import participant
from experiments.manager import experiment_manager
from experiments import conf

from uuid import uuid4

register = template.Library()


@register.inclusion_tag('experiments/goal.html')
def experiment_goal(goal_name):
    return {'url': reverse('experiment_goal', kwargs={'goal_name': goal_name, 'cache_buster': uuid4()})}


@register.inclusion_tag('experiments/confirm_human.html', takes_context=True)
def experiments_confirm_human(context):
    request = context.get('request')
    return {'confirmed_human': request.session.get(conf.CONFIRM_HUMAN_SESSION_KEY, False)}


class ExperimentNode(template.Node):
    def __init__(self, node_list, experiment_name, alternative, weight, user_variable):
        self.node_list = node_list
        self.experiment_name = experiment_name
        self.alternative = alternative
        self.weight = weight
        self.user_variable = user_variable

    def render(self, context):
        experiment = experiment_manager.get_experiment(self.experiment_name)
        if experiment:
            experiment.ensure_alternative_exists(self.alternative, self.weight)

        # Get User object
        if self.user_variable:
            auth_user = self.user_variable.resolve(context)
            user = participant(user=auth_user)
        else:
            request = context.get('request', None)
            user = participant(request)

        # Should we render?
        if user.is_enrolled(self.experiment_name, self.alternative):
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

    return ExperimentNode(node_list, experiment_name, alternative, weight, user_variable)


@register.simple_tag(takes_context=True)
def experiment_enroll(context, experiment_name, *alternatives, **kwargs):
    if 'user' in kwargs:
        user = participant(user=kwargs['user'])
    else:
        user = participant(request=context.get('request', None))
    return user.enroll(experiment_name, list(alternatives))
