# coding=utf-8
import re
import logging

from django.db import models
from django.template import Template, Context
from django.utils.encoding import python_2_unicode_compatible
from django.utils.safestring import mark_safe

from .utils import xml_bool


logger = logging.getLogger(__file__)


class ContextTemplateMixin(models.Model):
    """
    Mixing for models. Contains common fields and methods related to
    rendering the conditional template.
    """
    template = models.TextField(
        default='', blank=True, help_text=mark_safe(
            '<strong>Available XML tags:</strong><br /><code>'
            '&lt;true /&gt;<br />\n'
            '&lt;false /&gt;<br />\n'
            '&lt;all_of&gt;...&lt;/all_of&gt;<br />\n'
            '&lt;any_of&gt;...&lt;/any_of&gt;\n'
            '</code><br />'
            '<strong>Available template context:</strong><br />'
            'same as the template where {% experiments_auto_enroll %} is'
            ' being rendered.<br />'
            'Additional context injected from \'Context code\' field below.'
        ))
    context_code = models.TextField(
        default='', blank=True, null=False, help_text=mark_safe(
            'Python code that adds additional context to the conditional at '
            'run time. For extra safety, only names found in '
            '&lt;&lt;double angle braces&gt;&gt; will be injected into the '
            'context.'))

    variable_pattern = re.compile('<<([^<>]+)>>')

    class Meta:
        abstract = True

    def get_variables(self):
        """Extract <<varaible_names>> from template as a list of strings"""
        return self.variable_pattern.findall(self.template)

    @property
    def evaled_dict(self):
        return self._eval_context_code(self.context_code, fail_silently=True)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self._update_template_variables()
        super(ContextTemplateMixin, self).save(
            force_insert, force_update, using, update_fields)

    def _update_template_variables(self):
        """
        Looks for any <<variable>> (with double brackets) in self.template
        and makes sure they are defined in self.context_code as well.
        If missing, appends "variable = None" to context_code.
        """
        if self.context_code is None:
            self.context_code = ''
        self.context_code = self.context_code.strip()
        if self.context_code:
            self.context_code += '\n'

        exec_context = self._eval_context_code(
            self.context_code, fail_silently=True)

        for variable in self.get_variables():
            if variable not in exec_context:
                self.context_code += '{} = None\n'.format(variable)

    @staticmethod
    def _eval_context_code(context_code, fail_silently=False):
        """
        Produce a Python dict from self.context_code

        Uses `exec` which is EVIL (eval)!
        `self.context_code` must be trusted at all times.
        """
        exec_context = {}
        try:
            exec(context_code, exec_context)
        except Exception as e:
            if not fail_silently:
                raise
            logger.warning(ContextTemplateMixin._syntax_error_msg(e))
            return {}
        else:
            del exec_context['__builtins__']
            return exec_context

    @staticmethod
    def _syntax_error_msg(exc):
        return '{}, line {}: "{}"'.format(exc.msg, exc.lineno, exc.text)


class AdminConditional(ContextTemplateMixin, models.Model):
    """
    This model that evaluates a Django template (editable in the admin)
    to decide whether an experiment should be enrolled in at a given request.
    """
    experiment = models.ForeignKey(
        'Experiment',
        on_delete=models.CASCADE,
        related_name='admin_conditionals',
    )
    description = models.CharField(max_length=254, blank=True, null=False)
    copy_from = models.ForeignKey(
        'AdminConditionalTemplate', null=True, blank=True)

    class Meta:
        verbose_name = 'conditional'

    def __str__(self):
        return self.description

    def evaluate(self, request):
        """Produces a boolean value for this conditional+request pair"""
        context = request.experiments.context
        # eval from admin:
        template, approved_context = self._prepare_for_render()
        # add values from regular template context:
        complete_context = approved_context.copy()
        complete_context.update(context)
        # render the template:
        rendered_xml = self._render(template, complete_context)
        # parse the resulting domain-specific XML to get a boolean value:
        return xml_bool(rendered_xml)

    def _prepare_for_render(self):
        """
        Prepares context dict to be used when rendering (`exec`)
        self.template

        Only names found in the template surrounded by double angle
        brackets (e.g. <<like_this>>) are allowed to enter the context.
        Just being paranoid.

        Returns template string with brackets stripped and the context.
        """
        template = self.template
        approved_context = {}
        for variable, value in self.evaled_dict.items():
            template = re.sub(
                '<<{}>>'.format(variable),
                str(variable),
                template,
            )
            approved_context.update({variable: value})
        return template, approved_context

    @staticmethod
    def _render(template, context):
        """
        Renders the template using context. Wraps result in <any_of> tag
        """
        django_template = Template(template)
        rendered_template = '<any_of>{}</any_of>'.format(
            django_template.render(Context(context)))
        return rendered_template


@python_2_unicode_compatible
class AdminConditionalTemplate(ContextTemplateMixin, models.Model):
    """
    Used to create new AdminConditional instances.
    After creation, the new instances are not connected to this model,
    to allow free editing.
    """
    description = models.CharField(max_length=254, blank=False, null=False)

    class Meta:
        verbose_name = 'conditional template'
        ordering = ('description',)

    def __str__(self):
        return self.description


class ConditionalMixin(models.Model):
    """
    Mixin for Experiment model.
    Adds features related to conditional experiments.
    """
    auto_enroll = models.BooleanField(
        default=False, null=False, blank=True,
        help_text='Only experiments created via the admin are auto-enrollable.'
                  ' At least on of the conditionals below need to evaluate'
                  ' positively in order for the experiment to be enrollable.',
    )

    class Meta:
        abstract = True

    def should_auto_enroll(self, request):
        if not self.auto_enroll:
            return False
        if not self.is_accepting_new_users():
            return False
        if not self.has_alternatives:
            return False
        for conditional in self.admin_conditionals.all():
            if conditional.evaluate(request):
                return True
        return False
