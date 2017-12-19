# coding=utf-8
from django.test import (
    TestCase,
    RequestFactory,
)

from experiments.api.views import APIVersionsView


class ApiVersionsTestCase(TestCase):

    def test_get(self):
        view = APIVersionsView().as_view()
        request = RequestFactory().get('')
        response = view(request)
        self.assertIn('versions', response.data)
        self.assertIn('1.0', response.data['versions'])
        self.assertEqual(1, len(response.data['versions']))
        self.assertIn('http', response.data['versions']['1.0'])
