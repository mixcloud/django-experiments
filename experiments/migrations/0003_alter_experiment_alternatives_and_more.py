# Generated by Django 4.0.8 on 2022-10-31 10:11

import datetime
from django.db import migrations, models

try:
    from django.db.models import JSONField
except ImportError:  # Django < 3.1
    from jsonfield import JSONField


class Migration(migrations.Migration):

    dependencies = [
        ('experiments', '0002_auto_20201013_1408'),
    ]

    operations = [
        migrations.AlterField(
            model_name='experiment',
            name='alternatives',
            field=JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name='experiment',
            name='description',
            field=models.TextField(blank=True, default='', null=True),
        ),
        migrations.AlterField(
            model_name='experiment',
            name='relevant_chi2_goals',
            field=models.TextField(blank=True, default='', null=True),
        ),
        migrations.AlterField(
            model_name='experiment',
            name='relevant_mwu_goals',
            field=models.TextField(blank=True, default='', null=True),
        ),
        migrations.AlterField(
            model_name='experiment',
            name='start_date',
            field=models.DateTimeField(blank=True, db_index=True, default=datetime.datetime.now, null=True),
        ),
        migrations.AlterField(
            model_name='experiment',
            name='state',
            field=models.IntegerField(choices=[(0, 'Default/Control'), (1, 'Enabled'), (3, 'Track')], default=0),
        ),
    ]