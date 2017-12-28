# coding=utf-8
from __future__ import absolute_import
import json

from django.contrib.auth.models import User, Permission
from django.core.urlresolvers import reverse
from django.test import TestCase
from experiments.admin import ExperimentAdmin

from experiments.models import Experiment, CONTROL_STATE, ENABLED_STATE
from experiments.utils import participant
from experiments.tests.testing_2_3 import mock


class AdminAjaxTestCase(TestCase):
    def test_set_state(self):
        experiment = Experiment.objects.create(name='test_experiment', state=CONTROL_STATE)
        User.objects.create_superuser(username='user', email='deleted@mixcloud.com', password='pass')
        self.client.login(username='user', password='pass')

        self.assertEqual(Experiment.objects.get(pk=experiment.pk).state, CONTROL_STATE)
        response = self.client.post(reverse('admin:experiment_admin_set_state'), {
            'experiment': experiment.name,
            'state': ENABLED_STATE,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Experiment.objects.get(pk=experiment.pk).state, ENABLED_STATE)
        self.assertIsNone(Experiment.objects.get(pk=experiment.pk).end_date)

        response = self.client.post(reverse('admin:experiment_admin_set_state'), {
            'experiment': experiment.name,
            'state': CONTROL_STATE,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Experiment.objects.get(pk=experiment.pk).state, CONTROL_STATE)
        self.assertIsNotNone(Experiment.objects.get(pk=experiment.pk).end_date)

    def test_set_alternative(self):
        experiment = Experiment.objects.create(name='test_experiment', state=ENABLED_STATE)
        user = User.objects.create_superuser(username='user', email='deleted@mixcloud.com', password='pass')
        self.client.login(username='user', password='pass')

        participant(user=user).enroll('test_experiment', alternatives=['other1', 'other2'])

        for alternative in ('other2', 'control', 'other1'):
            response = self.client.post(reverse('admin:experiment_admin_set_alternative'), {
                'experiment': experiment.name,
                'alternative': alternative,
            })
            self.assertDictEqual(json.loads(response.content.decode('utf-8')), {
                'success': True,
                'alternative': alternative,
            })
            self.assertEqual(participant(user=user).get_alternative('test_experiment'), alternative)

    def test_permissions(self):
        # redirect to login if not logged in
        self.assertEqual(302, self.client.post(reverse('admin:experiment_admin_set_state'), {}).status_code)
        self.assertEqual(302, self.client.post(reverse('admin:experiment_admin_set_alternative'), {}).status_code)

        response = self.client.post(reverse('admin:experiment_admin_set_alternative'), {})
        self.assertEqual(response.status_code, 302)

        # non staff user
        user = User.objects.create_user(username='user', password='pass')
        user.save()
        self.client.login(username='user', password='pass')

        self.assertEqual(302, self.client.post(reverse('admin:experiment_admin_set_state'), {}).status_code)
        self.assertEqual(302, self.client.post(reverse('admin:experiment_admin_set_alternative'), {}).status_code)

        user.is_staff = True
        user.save()

        self.assertEqual(403, self.client.post(reverse('admin:experiment_admin_set_state'), {}).status_code)
        self.assertEqual(403, self.client.post(reverse('admin:experiment_admin_set_alternative'), {}).status_code)

        permission = Permission.objects.get(
            codename='change_experiment',
            content_type__app_label='experiments')
        user.user_permissions.add(permission)

        self.assertEqual(400, self.client.post(reverse('admin:experiment_admin_set_state'), {}).status_code)
        self.assertEqual(400, self.client.post(reverse('admin:experiment_admin_set_alternative'), {}).status_code)


class AdminTestCase(TestCase):

    def test_set_default_alternative_called_when_changed(self):
        obj = mock.MagicMock()
        request = mock.MagicMock()
        form = mock.MagicMock()
        changed = True
        model = Experiment
        admin_site = mock.MagicMock()
        admin_site = ExperimentAdmin(model, admin_site)

        admin_site.save_model(request, obj, form, changed)

        obj.set_default_alternative.assert_called_once_with(
            form.cleaned_data['default_alternative'])
        obj.save()

    def test_set_default_alternative_called_when_not_changed(self):
        obj = mock.MagicMock()
        request = mock.MagicMock()
        form = mock.MagicMock()
        changed = False
        model = Experiment
        admin_site = mock.MagicMock()
        admin_site = ExperimentAdmin(model, admin_site)

        admin_site.save_model(request, obj, form, changed)

        obj.set_default_alternative.assert_not_called()
        obj.save()
