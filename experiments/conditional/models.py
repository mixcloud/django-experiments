# coding=utf-8
from django.db import models


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

    def evaluate(self, request):
        context = request.experiments.context
        return self._parse_template(context)

    def _parse_template(self, context):
        # TODO actually implement
        return 'true' in self.template


class ConditionalMixin(models.Model):
    """
    Mixin for Experiment models.
    Adds features related to conditional experiments.
    """
    auto_enroll = models.BooleanField(
        default=False, null=False, blank=True,
        help_text='Automatically enroll visitors in this experiment if at'
                  ' least one of Conditionals (below) evaluates positively.',
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
