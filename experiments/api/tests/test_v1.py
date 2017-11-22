# coding=utf-8
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from experiments.models import Experiment

from experiments.api.v1.views import (
    APIRootView,
    ExperimentsListView,
    ExperimentView,
)


class ApiTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.user = User.objects.create(
            username='tester',
            is_staff=True,
        )

    @classmethod
    def tearDownClass(cls):
        cls.user.delete()

    def setUp(self):
        self.request = APIRequestFactory().get('')
        force_authenticate(self.request, user=self.user)
        Experiment.objects.all().delete()

    def test_root(self):
        view = APIRootView().as_view()
        response = view(self.request)
        self.assertIn('name', response.data)
        expected_name = settings.EXPERIMENTS_API['local']['name']
        self.assertIn(expected_name, response.data['name'])
        self.assertIn('experiments', response.data)
        self.assertIn('http', response.data['experiments'])

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
