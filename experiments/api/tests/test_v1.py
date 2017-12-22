# coding=utf-8
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from experiments.api.v1.views import (
    APIRootView,
    ExperimentsListView,
    ExperimentView,
)
import experiments
from experiments.models import Experiment
from experiments.tests.testing_2_3 import mock


test_api_settings = {
    'api_mode': 'client,server',
    'local': {
        'name': 'localhost',
    },
    'remotes': [
        {
            'url': 'http://matchingtool.consumeraffairs.caws',
            'token': 'localhost',
        },
    ],
}


class ApiTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.user = User.objects.create(
            username='tester',
            is_staff=True,
        )
        cls._original_conf_API = experiments.conf.API.copy()
        experiments.conf.API = test_api_settings

    @classmethod
    def tearDownClass(cls):
        cls.user.delete()
        experiments.conf.API = cls._original_conf_API

    def setUp(self):
        self.request = APIRequestFactory().get('')
        force_authenticate(self.request, user=self.user)
        Experiment.objects.all().delete()

    def test_root(self):
        view = APIRootView().as_view()
        response = view(self.request)
        self.assertIn('name', response.data)
        expected_name = test_api_settings['local']['name']
        self.assertIn(expected_name, response.data['name'])
        self.assertIn('experiments', response.data)
        self.assertIn('http', response.data['experiments'])

    @mock.patch('experiments.api.v1.views.conf')
    def test_root_not_server_mode(self, patched_conf):
        patched_conf.API['api_mode'] = 'client'
        view = APIRootView().as_view()
        response = view(self.request)
        self.assertIn('name', response.data)
        expected_name = test_api_settings['local']['name']
        self.assertIn(expected_name, response.data['name'])
        self.assertNotIn('experiments', response.data)

    def test_list(self):
        Experiment.objects.create(name='exp1')
        Experiment.objects.create(name='exp2')
        Experiment.objects.create(name='exp3')
        view = ExperimentsListView().as_view()
        response = view(self.request)
        self.assertIn('site', response.data)
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)
        self.assertEqual(3, len(response.data['results']))
        self.assertIn('http', response.data['results'][0]['url'])

    @mock.patch('experiments.api.v1.views.conf')
    def test_list_not_server_mode(self, patched_conf):
        patched_conf.API['api_mode'] = 'client'
        Experiment.objects.create(name='exp1')
        view = ExperimentsListView().as_view()
        response = view(self.request)
        self.assertEqual(403, response.status_code)
        self.assertEqual(b'', response.content)

    def test_single(self):
        Experiment.objects.create(name='exp1')
        Experiment.objects.create(name='exp2')
        Experiment.objects.create(name='exp3')

        view = ExperimentView().as_view()
        response = view(self.request, name='exp2')
        self.assertIn('site', response.data)
        self.assertIn('url', response.data)
        self.assertIn('http', response.data['url'])
        self.assertIn('name', response.data)
        self.assertEqual('exp2', response.data['name'])

    @mock.patch('experiments.api.v1.views.conf')
    def test_single_not_server_mode(self, patched_conf):
        patched_conf.API['api_mode'] = 'client'
        Experiment.objects.create(name='exp1')

        view = ExperimentView().as_view()
        response = view(self.request, name='exp2')
        self.assertEqual(403, response.status_code)
        self.assertEqual(b'', response.content)
