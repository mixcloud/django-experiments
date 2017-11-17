# coding=utf-8
from __future__ import absolute_import

import json
from django import template
from django.template import TemplateSyntaxError
from jinja2 import (
    ext,
    nodes,
)

import six

from ...templatetags.experiments import ExtensionHelpers
from ..enrollment import Experiments


if six.PY2:
    # Python 2's next() can't handle a non-iterator with a __next__ method.
    _next = next
    def next(obj, _next=_next):
        if getattr(obj, '__next__', None):
            return obj.__next__()
        return _next(obj)

    del _next


register = template.Library()


def _auto_enroll(context):
    Experiments(context)
    request = context['request']
    if request.user.is_staff:
        report = json.dumps(request.experiments.report)
        script = '<script>window.ca_experiments = {};</script>'.format(
            report,
        )
        return script
    return ''


def _experiment_conditional_alternative(context, experiment_name):
    try:
        experiments = context['request'].experiments
    except AttributeError:
        return ''
    return experiments.get_conditionally_enrolled_alternative(experiment_name)


@register.simple_tag(takes_context=True)
def experiments_auto_enroll(context):
    """Template tag for regular Django templates"""
    return _auto_enroll(context)


@register.simple_tag(takes_context=True)
def experiment_conditional_alternative(context, experiment_name):
    """Template tag for regular Django templates"""
    return _experiment_conditional_alternative(context, experiment_name)


class AutoEnrollExperimentsExtension(ExtensionHelpers, ext.Extension):
    """Jinja2 Extension for experiments_auto_enroll"""
    tags = {
        'experiments_auto_enroll',
        'experiment_conditional_alternative',
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

    def parse_experiments_auto_enroll(self, parser):
        """Parse {% experiments_auto_enroll %} tags"""
        lineno = parser.stream.current.lineno
        # list of nodes that will be used when calling the callback:
        args = []
        args.append(nodes.ContextReference())
        # Jinja2 callbacky nodey magic:
        call_node = self.call_method(
            'render_experiments_auto_enroll', args, lineno=lineno)
        return nodes.CallBlock(call_node, [], [], []).set_lineno(lineno)

    def render_experiments_auto_enroll(self, context, caller):
        """Callback that renders {% experiments_auto_enroll %} tag"""
        return nodes.Markup(_auto_enroll(context))

    def parse_experiment_conditional_alternative(self, parser):
        """
        Parse {% experiments_conditional_alternative <experiment_name> %} tags
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
            'render_experiment_conditional_alternative', args, lineno=lineno)

        # return an assignment node that will trigger the callback:
        return nodes.Assign(target, call_node, lineno=lineno)

    def render_experiment_conditional_alternative(self, experiment_name, context):
        """
        Callback to render {% experiment_enrolled_alternative ... %} tags.

        This method does not actually render anything, but is called at
        render time so keeping the name for consistency.
        Result gets added ("assigned") back into template context.
        """
        alternative = _experiment_conditional_alternative(
            context, experiment_name)
        return alternative
