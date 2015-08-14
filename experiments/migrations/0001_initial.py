# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import jsonfield.fields
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Enrollment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('enrollment_date', models.DateTimeField(auto_now_add=True)),
                ('last_seen', models.DateTimeField(null=True)),
                ('alternative', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Experiment',
            fields=[
                ('name', models.CharField(max_length=128, serialize=False, primary_key=True)),
                ('description', models.TextField(default=b'', null=True, blank=True)),
                ('alternatives', jsonfield.fields.JSONField(default={}, blank=True)),
                ('relevant_chi2_goals', models.TextField(default=b'', null=True, blank=True)),
                ('relevant_mwu_goals', models.TextField(default=b'', null=True, blank=True)),
                ('state', models.IntegerField(default=0, choices=[(0, b'Default/Control'), (1, b'Enabled'), (3, b'Track')])),
                ('start_date', models.DateTimeField(default=django.utils.timezone.now, null=True, db_index=True, blank=True)),
                ('end_date', models.DateTimeField(null=True, blank=True)),
            ],
        ),
        migrations.AddField(
            model_name='enrollment',
            name='experiment',
            field=models.ForeignKey(to='experiments.Experiment'),
        ),
        migrations.AddField(
            model_name='enrollment',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='enrollment',
            unique_together=set([('user', 'experiment')]),
        ),
    ]
