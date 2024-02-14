from django.db import IntegrityError
from django.core.management import BaseCommand

from experiments.models import Experiment


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='Chosen name for this experiment'),
        parser.add_argument('alternatives', metavar='alternative', type=str, nargs='+', help='New alternative names ("control" is automatically created)'),
        parser.add_argument('--add', default=False, type=bool, help='Add alternatives to an existing experiment rather than create a new one'),

    def handle(self, *args, **options):
        if options['add']:
            try:
                experiment = Experiment.objects.get(name=options['name'])
            except Experiment.DoesNotExist:
                self.stdout.write(self.style.ERROR("Could not find an experiment named '%s'" % options['name']))
                return
        else:
            try:
                experiment = Experiment.objects.create(name=options['name'])
            except IntegrityError:
                self.stdout.write(self.style.ERROR("An experiment named '%s' already exists" % options['name']))
                return

        for alternative in options['alternatives']:
            if ':' in alternative:
                alternative, weight = alternative.split(':')
                experiment.ensure_alternative_exists(alternative, weight)
            else:
                experiment.ensure_alternative_exists(alternative)

        self.stdout.write(self.style.SUCCESS("Experiment '%s' created" % experiment.name))
