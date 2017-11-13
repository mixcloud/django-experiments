# coding=utf-8
from __future__ import absolute_import

import json
from django import template
from jinja2 import (
    ext,
    nodes,
)

from ..utils import Experiments


register = template.Library()


def _auto_enroll(context):
    request = context['request']
    request.experiments = Experiments(context)
    request.experiments.conditionally_enroll()
    if request.user.is_staff:
        report = json.dumps(request.experiments.report)
        script = '<script>window.ca_experiments = {};</script>'.format(
            report,
        )
        return script
    return ''


@register.simple_tag(takes_context=True)
def experiments_auto_enroll(context):
    """Template tag for regular Django templates"""
    return _auto_enroll(context)


class AutoEnrollExperimentsExtension(ext.Extension):
    """Jinja2 Extension for experiments_auto_enroll"""
    tags = {
        'experiments_auto_enroll',
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
