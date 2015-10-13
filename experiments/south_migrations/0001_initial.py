# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration

try:
    from django.contrib.auth import get_user_model
except ImportError:  # django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()


class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Experiment'
        db.create_table('experiments_experiment', (
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128, primary_key=True)),
            ('description', self.gf('django.db.models.fields.TextField')(default='', null=True, blank=True)),
            ('alternatives', self.gf('jsonfield.fields.JSONField')(default='{}', blank=True)),
            ('relevant_goals', self.gf('django.db.models.fields.TextField')(default='', null=True, blank=True)),
            ('switch_key', self.gf('django.db.models.fields.CharField')(default='', max_length=50, null=True, blank=True)),
            ('state', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('start_date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, null=True, db_index=True, blank=True)),
            ('end_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('experiments', ['Experiment'])

        # Adding model 'Enrollment'
        db.create_table('experiments_enrollment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm["%s.%s" % (User._meta.app_label, User._meta.object_name)], null=True)),
            ('experiment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['experiments.Experiment'])),
            ('enrollment_date', self.gf('django.db.models.fields.DateField')(auto_now_add=True, db_index=True, blank=True)),
            ('alternative', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('goals', self.gf('jsonfield.fields.JSONField')(default='[]', blank=True)),
        ))
        db.send_create_signal('experiments', ['Enrollment'])

        # Adding unique constraint on 'Enrollment', fields ['user', 'experiment']
        db.create_unique('experiments_enrollment', ['user_id', 'experiment_id'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Enrollment', fields ['user', 'experiment']
        db.delete_unique('experiments_enrollment', ['user_id', 'experiment_id'])

        # Deleting model 'Experiment'
        db.delete_table('experiments_experiment')

        # Deleting model 'Enrollment'
        db.delete_table('experiments_enrollment')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        "%s.%s" % (User._meta.app_label, User._meta.module_name): {
            'Meta': {'object_name': User.__name__ },
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
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
            'goals': ('jsonfield.fields.JSONField', [], {'default': "'[]'", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s.%s']" % (User._meta.app_label, User._meta.object_name), 'null': 'True'})
        },
        'experiments.experiment': {
            'Meta': {'object_name': 'Experiment'},
            'alternatives': ('jsonfield.fields.JSONField', [], {'default': "'{}'", 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'primary_key': 'True'}),
            'relevant_goals': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'switch_key': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['experiments']
