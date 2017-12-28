# coding=utf-8
from django.test import TestCase
from django.utils import timezone

from experiments.api.admin import RemoteExperimentAdmin

from experiments.api.models import RemoteExperiment, RemoteApiException
from experiments.tests.testing_2_3 import mock


class AdminTestCase(TestCase):

    def setUp(self):
        self.request = mock.MagicMock()
        self.site = mock.MagicMock()
        self.modeladmin = RemoteExperimentAdmin(RemoteExperiment, self.site)
        self.kwargs = {
            'site': 'Some remote site',
            'name': 'Some experiment',
            'url': 'Some URL',
            'admin_url': 'Some admin URL',
            'state': 1,
            'start_date': timezone.datetime(2001, 2, 3, 0, 1, 2),
            'end_date': timezone.datetime(2001, 2, 3, 3, 4, 5),
            'alternatives_list': ['alt1', 'alt2', 'control'],
            'statistics': {
                'alternatives': {
                    'alt1': 11,
                    'alt2': 22,
                    'control': 33,
                },
                'results': {
                    "goal_1": {
                        "control": {
                            "conversion_rate": 0.0,
                            "average_goal_actions": None,
                            "conversions": 0
                        },
                        "is_primary": True,
                        "relevant": True,
                        "alternatives": [
                            [
                                'alt1',
                                {
                                    "conversion_rate": 100.0,
                                    "confidence": None,
                                    "improvement": 0.0,
                                    "mann_whitney_confidence": None,
                                    "average_goal_actions": 3.310344827586207,
                                    "conversions": 29
                                },
                            ],
                            [
                                'alt2',
                                {
                                    "conversion_rate": 95.0,
                                    "confidence": 34.56,
                                    "improvement": 0.0,
                                    "mann_whitney_confidence": None,
                                    "average_goal_actions": 1.9666666666666666,
                                    "conversions": 30
                                },
                            ],
                        ]
                    },
                    "goal_2": {
                        "control": {
                            "conversion_rate": 0.0,
                            "average_goal_actions": None,
                            "conversions": 0
                        },
                        "is_primary": False,
                        "relevant": True,
                        "alternatives": [
                            [
                                'alt1',
                                {
                                    "conversion_rate": 10.0,
                                    "confidence": 11.22,
                                    "improvement": 0.0,
                                    "mann_whitney_confidence": None,
                                    "average_goal_actions": 1.1111,
                                    "conversions": 2
                                },
                            ],
                            [
                                'alt2',
                                {
                                    "conversion_rate": 15.0,
                                    "confidence": 67.89,
                                    "improvement": 0.0,
                                    "mann_whitney_confidence": None,
                                    "average_goal_actions": 2.2222,
                                    "conversions": 3
                                },
                            ],
                        ]
                    },
                },
            },
            'batch': 14,
        }
        RemoteExperiment.objects.all().delete()
        self.obj = RemoteExperiment.objects.create(**self.kwargs)

    def test_admin_link(self):
        value = self.modeladmin.admin_link(self.obj)
        self.assertIn('<a href', value)
        self.assertIn('Some admin URL', value)

    def test_state_toggle(self):
        value = self.modeladmin.state_toggle(self.obj)
        self.assertIn('<a href', value)
        self.assertIn('Default/Control', value)
        self.assertIn('data-id="{}"'.format(self.obj.id), value)

    @mock.patch('experiments.api.admin.STATES')
    def test_state_toggle_w_no_states_lol(self, STATES):
        STATES = {}
        value = self.modeladmin.state_toggle(self.obj)
        self.assertEqual('<div class="state_toggle"></div>', value)

    def test_participants(self):
        value = self.modeladmin.participants(self.obj)
        self.assertEqual(66, value)

    def test_confidences_no_alternatives(self):
        self.obj.alternatives_list = []
        value = self.modeladmin.confidences(self.obj)
        self.assertEqual('no alternatives', value)

    def test_confidences_no_primary_goals(self):
        self.obj.statistics['results']['goal_1']['is_primary'] = False
        value = self.modeladmin.confidences(self.obj)
        self.assertEqual('no primary goals', value)

    def test_confidences_minitable(self):
        value = self.modeladmin.confidences(self.obj)
        self.assertIn('<table class="ministats">', value)
        self.assertIn('34.56%', value)
        self.assertNotIn('67.89%', value)

    def test_has_delete_permission(self):
        value = self.modeladmin.has_delete_permission(self.request, self.obj)
        self.assertFalse(value)

    def test_has_add_permission(self):
        value = self.modeladmin.has_add_permission(self.request)
        self.assertFalse(value)

    @mock.patch('django.contrib.admin.ModelAdmin.get_actions')
    def test_get_actions_w_delete(self, mock_super):
        mock_super.return_value = {
            'delete_selected': 'foo',
            'another_action': 'bar',
        }
        value = self.modeladmin.get_actions(self.request)
        self.assertNotIn('delete_selected', value)
        self.assertIn('another_action', value)
        self.assertEqual(value['another_action'], 'bar')

    @mock.patch('django.contrib.admin.ModelAdmin.get_actions')
    def test_get_actions_wo_delete(self, mock_super):
        mock_super.return_value = {
            'another_action': 'bar',
        }
        value = self.modeladmin.get_actions(self.request)
        self.assertIn('another_action', value)
        self.assertEqual(value['another_action'], 'bar')

    @mock.patch('experiments.api.models.RemoteExperiment.update_remotes')
    @mock.patch('django.contrib.admin.ModelAdmin.changelist_view')
    @mock.patch('django.contrib.admin.ModelAdmin.message_user')
    def test_changelist_view_triggers_sync(
            self, message_user, mock_super, update_remotes):
        mock_super.return_value = 'super changelist'
        update_remotes.return_value = []

        value = self.modeladmin.changelist_view(self.request)

        self.assertEqual('super changelist', value)
        update_remotes.assert_called_once_with()
        message_user.assert_not_called()

    @mock.patch('experiments.api.models.RemoteExperiment.update_remotes')
    @mock.patch('django.contrib.admin.ModelAdmin.changelist_view')
    @mock.patch('django.contrib.admin.ModelAdmin.message_user')
    def test_changelist_view_triggers_sync_w_exceptions(
            self, message_user, mock_super, update_remotes):
        mock_super.return_value = 'super changelist'
        exc = RemoteApiException(
            server={'url':'some url'},
            original_exception=ValueError('some error'))
        update_remotes.return_value = [exc]

        value = self.modeladmin.changelist_view(self.request)

        self.assertEqual('super changelist', value)
        update_remotes.assert_called_once_with()
        message_user.assert_called_once_with(
            self.request,
            "Error updating from some url: ValueError('some error',)",
        )
