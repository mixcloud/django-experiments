# coding=utf-8
from __future__ import absolute_import
import json

from django.contrib.auth.models import User, Permission
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import timezone
from experiments.admin import ExperimentAdmin, ExperimentResource

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


class ExperimentResourceTestCase(TestCase):

    def setUp(self):
        self.experiment = Experiment.objects.create(
            name='test_experiment',
            state=ENABLED_STATE,
            start_date=timezone.datetime(2017,12,21),
        )
        self.experiment_resource = ExperimentResource()
        self.stat = {
            'alternatives': [('control', 10), ('alt1', 100), ('alt2', 1000)],
            'results': {
                'test_goal_1': {
                    'control': {
                        'conversions': 1,
                        'average_goal_actions': 1.0,
                        'conversion_rate': 100.0
                    },
                    'relevant': True,
                    'is_primary': True,
                    'alternatives': [('alt1', {
                        'conversions': 0,
                        'confidence': None,
                        'mann_whitney_confidence': None
                    }), ('alt2', {
                        'conversions': 11,
                        'confidence': 0,
                        'mann_whitney_confidence': None
                    })],
                },
                'test_goal_2': {
                    'control': {
                        'conversions': 0,
                        'average_goal_actions': None,
                        'conversion_rate': 0.0
                    },
                    'relevant': True,
                    'is_primary': True,
                    'alternatives': [('alt1', {
                        'conversions': 0,
                        'confidence': None,
                        'mann_whitney_confidence': None
                    }), ('alt2', {
                        'conversions': 1,
                        'confidence': 84.27007929422173,
                        'mann_whitney_confidence': None
                    })],
                },
                'test_goal_3': {
                    'control': {
                        'conversions': 0,
                        'average_goal_actions': None,
                        'conversion_rate': 0.0
                    },
                    'relevant': True,
                    'is_primary': False,
                    'alternatives': [('alt1', {
                        'conversions': 0,
                        'confidence': None,
                        'mann_whitney_confidence': None
                    }), ('alt2', {
                        'conversions': 1,
                        'confidence': 0.0001,
                        'mann_whitney_confidence': None
                    })],
                }
            },
        }

    def test_dehydrate_created_date(self):
        actual = self.experiment_resource.dehydrate_created_date(
            self.experiment)
        expected = timezone.datetime(2017, 12, 21).date()
        self.assertEqual(expected, actual)

    def test_dehydrate_state(self):
        actual = self.experiment_resource.dehydrate_state(self.experiment)
        expected = "Enabled"
        self.assertEqual(expected, actual)

    @mock.patch('experiments.admin.get_experiment_stats')
    def test_dehydrate_participants(self, get_experiment_stats):
        get_experiment_stats.return_value = self.stat

        actual = self.experiment_resource.dehydrate_participants(
            self.experiment)

        expected = "control: 10, \nalt1: 100, \nalt2: 1000"
        get_experiment_stats.assert_called_once_with(self.experiment)
        self.assertEqual(expected, actual)

    @mock.patch('experiments.admin.get_experiment_stats')
    def test_dehydrate_statistic(self, get_experiment_stats):
        get_experiment_stats.return_value = self.stat

        actual = self.experiment_resource.dehydrate_statistic(
            self.experiment)

        self.assertIn('test_goal_1/alt1: N/A', actual)
        self.assertIn('test_goal_1/alt2: 0.00%', actual)
        self.assertIn('test_goal_2/alt2: 84.27%', actual)
        self.assertNotIn('test_goal_3/alt1', actual)
        get_experiment_stats.assert_called_once_with(self.experiment)

    @mock.patch('experiments.admin.get_experiment_stats')
    def test_dehydrate_conversion(self, get_experiment_stats):
        get_experiment_stats.return_value = self.stat

        actual = self.experiment_resource.dehydrate_conversion(
            self.experiment)

        self.assertIn('test_goal_1/alt1: 0', actual)
        self.assertIn('test_goal_1/alt2: 11', actual)
        self.assertNotIn('test_goal_3/alt1', actual)
        get_experiment_stats.assert_called_once_with(self.experiment)
