# coding=utf-8
from __future__ import absolute_import

from operator import attrgetter
from uuid import uuid4

from django import template
from django.core.urlresolvers import reverse
from jinja2 import (
    ext,
    nodes,
    TemplateSyntaxError,
)
import six

from experiments.utils import participant
from experiments.manager import experiment_manager
from experiments import conf


if six.PY2:
    # Python 2's next() can't handle a non-iterator with a __next__ method.
    _next = next
    def next(obj, _next=_next):
        if getattr(obj, '__next__', None):
            return obj.__next__()
        return _next(obj)

    del _next


register = template.Library()


@register.inclusion_tag('experiments/goal.html')
def experiment_goal(goal_name):
    return _experiment_goal(goal_name)


def _experiment_goal(goal_name):
    return {
        'url': reverse(
            'experiment_goal',
            kwargs={'goal_name': goal_name, 'cache_buster': uuid4()},
        ),
    }


@register.inclusion_tag('experiments/confirm_human.html', takes_context=True)
def experiments_confirm_human(context):
    return _experiments_confirm_human(context)


def _experiments_confirm_human(context):
    request = context['request']
    return {'confirmed_human': request.session.get(conf.CONFIRM_HUMAN_SESSION_KEY, False)}


class ExperimentNode(template.Node):
    def __init__(
            self, node_list, experiment_name, alternative, weight,
            user_variable):
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
    (
        (_, experiment_name, alternative),
        remaining_tokens,
    ) = token_contents[:3], token_contents[3:]
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
    
    If the alternative name is neither 'test'
    nor 'control' an exception is raised
    during rendering.
    """
    try:
        token_contents = token.split_contents()
        (
            experiment_name,
            alternative,
            weight,
            user_variable,
        ) = _parse_token_contents(token_contents)

        node_list = parser.parse(('endexperiment', ))
        parser.delete_first_token()
    except ValueError:
        raise template.TemplateSyntaxError(
            "Syntax should be like: "
            "{% experiment experiment_name alternative"
            " [weight=val] [user=val] %}")

    return ExperimentNode(
        node_list, experiment_name, alternative, weight, user_variable)


@register.assignment_tag(takes_context=True)
def experiment_enroll(context, experiment_name, *alternatives, **kwargs):
    return _experiment_enroll(
        context, experiment_name, *alternatives, **kwargs)


def _experiment_enroll(context, experiment_name, *alternatives, **kwargs):
    if 'user' in kwargs:
        user = participant(user=kwargs['user'])
    else:
        user = participant(request=context.get('request', None))
    return user.enroll(experiment_name, list(alternatives))


@register.assignment_tag(takes_context=True)
def experiment_enrolled_alternative(context, experiment_name):
    return _experiment_enrolled_alternative(context, experiment_name)


def _experiment_enrolled_alternative(context, experiment_name):
    user = participant(request=context.get('request', None))
    return user.get_alternative(experiment_name)


class ExperimentsExtension(ext.Extension):
    """Jinja2 Extension for django-experiments"""

    # tags that will be handled by this class:
    tags = {
        'experiment',
        'experiments_confirm_human',
        'experiment_enroll',
        'experiment_enrolled_alternative',
        'experiment_goal',
    }

    def parse(self, parser):
        """
        Read the first token of a tag (i.e. the tag name)
        and call appropriate parser method.

        Parse methods are executed only once per process, when templates
        compile for the first time.

        Conversely, `render_*()` methods (i.e. callbacks) are executed
        on every render.
        """
        # first token, i.e. the tag name:
        tag = parser.stream.current.value
        next(parser.stream)
        return getattr(self, 'parse_{}'.format(tag))(parser)

    def parse_experiment(self, parser):
        """Parse {% experiment ... %} tags"""

        lineno = parser.stream.current.lineno

        # list of nodes that will be used when calling the callback:
        args = []

        # get tag parameters:
        while parser.stream.current.type != 'block_end':
            if parser.stream.skip_if('comma'):
                continue  # just ignore commas
            # {% experiment %} tag only accepts strings, i.e. Const:
            args.append(nodes.Const(parser.stream.current.value))
            next(parser.stream)

        # verify tag syntax:
        tokens = [nodes.Const('experiment')] + args
        try:
            _parse_token_contents(list(map(attrgetter('value'), tokens)))
        except ValueError:
            raise TemplateSyntaxError(
                "Syntax should be like: "
                "{% experiment experiment_name"
                " alternative [weight=val] [user=val] %}",
                lineno,
            )

        # fill in default values:
        while len(args) < 4:
            args.append(nodes.Const(None))

        # additional args:
        args.append(nodes.ContextReference())

        # parse the body of the block up to `endexperiment` and
        # drop the needle (which will always be `endexperiment`):
        body = parser.parse_statements(
            ['name:endexperiment'], drop_needle=True)

        # Jinja2 callbacky nodey magic:
        call_node = self.call_method('render_experiment', args, lineno=lineno)
        return nodes.CallBlock(call_node, [], [], body).set_lineno(lineno)

    def render_experiment(
            self, experiment_name, alternative, weight, user_variable,
            context, caller):
        """Callback to render {% experiment ... %} tags"""

        experiment = experiment_manager.get_experiment(experiment_name)
        if experiment:
            # create alternative on the fly (write it to DB) if not existing:
            experiment.ensure_alternative_exists(alternative, weight)

        # Get User object
        if user_variable:
            auth_user = context[user_variable]
            user = participant(user=auth_user)
        else:
            request = context.get('request')
            user = participant(request)

        # Should we render?
        if user.is_enrolled(experiment_name, alternative):
            return caller()
        else:
            return nodes.Markup()  # empty node

    def parse_experiments_confirm_human(self, parser):
        """Parse {% experiments_confirm_human %} tags"""
        lineno = parser.stream.current.lineno
        args = [nodes.ContextReference()]
        node = self.call_method(
            'render_experiments_confirm_human', args, lineno=lineno)
        return nodes.CallBlock(node, [], [], []).set_lineno(lineno)

    def render_experiments_confirm_human(self, context, caller):
        """Callback to render {% experiments_confirm_human %} tags"""
        tmplt = template.loader.get_template('experiments/confirm_human.html')
        context_dict = dict(context)
        context_dict.update(
            _experiments_confirm_human(context_dict)
        )
        return tmplt.render(context_dict)

    def parse_experiment_goal(self, parser):
        """Parse {% experiment_goal ... %} tags"""
        lineno = parser.stream.current.lineno
        args = [nodes.ContextReference()]
        goal_name = parser.stream.current
        args.append(self._name_or_const(goal_name))
        next(parser.stream)
        node = self.call_method(
            'render_experiment_goal', args, lineno=lineno)
        return nodes.CallBlock(node, [], [], []).set_lineno(lineno)

    def render_experiment_goal(self, context, goal_name, caller):
        """Callback to render {% experiment_goal ... %} tags"""
        tmplt = template.loader.get_template('experiments/goal.html')
        context_dict = dict(context)
        context_dict.update(
            _experiment_goal(goal_name)
        )
        return tmplt.render(context_dict)

    def parse_experiment_enroll(self, parser):
        """Parse {% experiment_enroll ... %} tags"""

        lineno = parser.stream.current.lineno

        # list of nodes that will be used when calling the callback:
        args = []

        # parsing first parameter:
        experiment_name = parser.stream.current
        args.append(self._name_or_const(experiment_name))
        next(parser.stream)

        # parsing remaining parameters (the "alternatives"):
        alternatives = []
        while parser.stream.current.type != 'block_end':
            if self._token_as(parser):
                break
            alternatives.append(self._name_or_const(parser.stream.current))
            next(parser.stream)
        args.append(nodes.List(alternatives))

        # expecting `as` after the alternatives:
        if not self._token_as(parser):
            raise TemplateSyntaxError(
                'Syntax should be like: '
                '{% experiment_enroll "experiment_name"'
                ' "alternative1" "alternative2" ... as some_variable %}',
                lineno,
            )
        next(parser.stream)

        # parse what comes after `as`:
        target = parser.parse_assign_target()

        # We're done with parsing the tag.

        # we will also need the context in the callback:
        args.append(nodes.ContextReference())

        # create a callback node that will be executed on render:
        call_node = self.call_method(
            'render_experiment_enroll', args, lineno=lineno)

        # return an assignment node that will trigger the callback:
        return nodes.Assign(target, call_node, lineno=lineno)

    def render_experiment_enroll(self, experiment_name, alternatives, context):
        """
        Callback to render {% experiment_enroll ... %} tags.

        This method does not actually render anything, but is called at
        render time so keeping the name for consistency.
        Result gets added ("assigned") back into template context.
        """
        return _experiment_enroll(context, experiment_name, *alternatives)

    def parse_experiment_enrolled_alternative(self, parser):
        """
        Parse {% experiment_enrolled_alternative <experiment_name> %} tags
        """

        lineno = parser.stream.current.lineno

        # list of nodes that will be used when calling the callback:
        args = []

        # get experiment name from token
        experiment_name = parser.stream.current
        args.append(self._name_or_const(experiment_name))
        next(parser.stream)

        # we will also need the context in the callback:
        args.append(nodes.ContextReference())

        # expecting `as` after the alternatives:
        if not self._token_as(parser):
            raise TemplateSyntaxError(
                'Syntax should be like: '
                '{% experiment_enrolled_alternative "experiment_name"'
                ' as some_variable %}',
                lineno,
            )
        next(parser.stream)

        # parse what comes after `as`:
        target = parser.parse_assign_target()

        # create a callback node that will be executed on render:
        call_node = self.call_method(
            'render_experiment_enrolled_alternative', args, lineno=lineno)

        # return an assignment node that will trigger the callback:
        return nodes.Assign(target, call_node, lineno=lineno)

    def render_experiment_enrolled_alternative(self, experiment_name, context):
        """
        Callback to render {% experiment_enrolled_alternative ... %} tags.

        This method does not actually render anything, but is called at
        render time so keeping the name for consistency.
        Result gets added ("assigned") back into template context.
        """
        alternative = _experiment_enrolled_alternative(
            context, experiment_name)
        return alternative

    # helpers #

    def _name_or_const(self, token):
        """
        Depending on what was provided in a tag as an argument, we need
        either `nodes.Const` (if a string was provided), or `nodes.Name`
        (if a variable name was provided).

        Not tested with integers etc.

        Maybe there exists a `stream.parse_something()` method that
        should we used instead?
        """
        if token.type == 'name':
            return nodes.Name(token.value, 'load')
        if token.type == 'string':
            return nodes.Const(token.value)
        raise ValueError('Expected name or string, got {}'.format(token))

    def _token_as(self, parser):
        """
        Return True if current token is an `as`.

        `token.type` will be `as` if there are no names used in the tag.
        If there are names (i.e. variables) used, then `as` will also be
        considered a "name", hence the extended check.
        """
        current_token = parser.stream.current
        return (
            current_token.type == 'as' or
            (current_token.type == 'name' and current_token.value == 'as')
        )
