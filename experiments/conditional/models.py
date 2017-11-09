# coding=utf-8
from django.db import models
from django.template import Template, Context
from django.utils.encoding import python_2_unicode_compatible


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
    description = models.CharField(max_length=254, blank=False, null=False)
    template = models.TextField(default='')

    class Meta:
        verbose_name = 'conditional'

    @python_2_unicode_compatible
    def __str__(self):
        return self.description

    def evaluate(self, request):
        context = request.experiments.context
        return self._parse_template(context)

    def _parse_template(self, context):
        # TODO actually implement
        django_template = Template(self.template)
        rendered_template = django_template.render(Context(context))
        return 'true' in rendered_template


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
