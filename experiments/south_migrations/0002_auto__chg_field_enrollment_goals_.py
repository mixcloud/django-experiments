# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

try:
    from django.contrib.auth import get_user_model
except ImportError:  # django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()


class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'Enrollment.goals'
        db.alter_column('experiments_enrollment', 'goals', self.gf('jsonfield.fields.JSONField')(null=True, blank=True))

        # Adding field 'Experiment.relevant_chi2_goals'
        db.add_column('experiments_experiment', 'relevant_chi2_goals', self.gf('django.db.models.fields.TextField')(default='', null=True, blank=True), keep_default=False)

        # Adding field 'Experiment.relevant_mwu_goals'
        db.add_column('experiments_experiment', 'relevant_mwu_goals', self.gf('django.db.models.fields.TextField')(default='', null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Changing field 'Enrollment.goals'
        db.alter_column('experiments_enrollment', 'goals', self.gf('jsonfield.fields.JSONField')(blank=True))

        # Deleting field 'Experiment.relevant_chi2_goals'
        db.delete_column('experiments_experiment', 'relevant_chi2_goals')

        # Deleting field 'Experiment.relevant_mwu_goals'
        db.delete_column('experiments_experiment', 'relevant_mwu_goals')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        "%s.%s" % (User._meta.app_label, User._meta.module_name): {
            'Meta': {'object_name': User.__name__ },
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'experiments.enrollment': {
            'Meta': {'unique_together': "(('user', 'experiment'),)", 'object_name': 'Enrollment'},
            'alternative': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'enrollment_date': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['experiments.Experiment']"}),
            'goals': ('jsonfield.fields.JSONField', [], {'default': "'{}'", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s.%s']" % (User._meta.app_label, User._meta.object_name), 'null': 'True'})
        },
        'experiments.experiment': {
            'Meta': {'object_name': 'Experiment'},
            'alternatives': ('jsonfield.fields.JSONField', [], {'default': "'{}'", 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'primary_key': 'True'}),
            'relevant_chi2_goals': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'relevant_mwu_goals': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'switch_key': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['experiments']
