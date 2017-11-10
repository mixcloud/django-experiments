# coding=utf-8
import re

from django.db import models
from django.template import Template, Context
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property

from .utils import xml_bool


class AdminConditional(models.Model):
    """
    This model that evaluates a Django template (editable in the admin)
    to decide whether an experiment should be enrolled in at a giver request.
    """
    experiment = models.ForeignKey(
        'Experiment',
        on_delete=models.CASCADE,
        related_name='admin_conditionals',
    )
    description = models.CharField(max_length=254, blank=True, null=False)
    template = models.TextField(default='', blank=True)
    copy_from = models.ForeignKey(
        'AdminConditionalTemplate', null=True, blank=True)
    template_values = models.TextField(default='', blank=True)

    variable_pattern = re.compile('<<([^<>]+)>>')

    class Meta:
        verbose_name = 'conditional'

    @python_2_unicode_compatible
    def __str__(self):
        return self.description

    def evaluate(self, request):
        context = request.experiments.context
        return self._parse_template(context)

    def _parse_template(self, context):
        # substitute variables
        template = self.template
        for variable, value in self.variable_values:
            template = re.sub(
                '<<{}>>'.format(variable),
                value,
                template,
            )
        template = self.variable_pattern.sub('', template)

        # render with Django engine
        django_template = Template(template)
        rendered_template = '<any_of>{}</any_of>'.format(
            django_template.render(Context(context)))
        return xml_bool(rendered_template)

    def get_variables(self):
        return self.variable_pattern.findall(self.template)

    @cached_property
    def variable_values(self):
        lines = self.template_values.split('\n')
        lines = filter(None, map(str.strip, lines))
        for line in lines:
            key, value = line.split(':', 1)
            yield key.strip(), value.strip()

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self._update_template_varialbes()
        super(AdminConditional, self).save(
            force_insert, force_update, using, update_fields)

    def _update_template_varialbes(self):
        missing_variables = set()
        defined_variables = [k for k, _ in self.variable_values]
        for variable in self.get_variables():
            if variable not in defined_variables:
                missing_variables.add(variable)
        if self.template_values and not self.template_values.endswith('\n'):
            self.template_values += '\n'
        for missing_variable in missing_variables:
            self.template_values += '{}: \n'.format(missing_variable)


class AdminConditionalTemplate(models.Model):
    """

    """
    description = models.CharField(max_length=254, blank=False, null=False)
    template = models.TextField(default='', blank=True)

    class Meta:
        verbose_name = 'conditional template'
        ordering = ('description',)

    @python_2_unicode_compatible
    def __str__(self):
        return self.description


class ConditionalMixin(models.Model):
    """
    Mixin for Experiment models.
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
