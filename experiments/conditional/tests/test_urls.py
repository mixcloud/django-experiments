# coding=utf-8
from __future__ import absolute_import

from unittest import TestCase, skipIf

from django.conf.urls import RegexURLPattern
from django.views.generic import View
from django import VERSION as DJANGO_VERSION

from ..views import ExperimentsMixin
from ..urls import experimentize, url


@skipIf(DJANGO_VERSION < (1, 9), 'Unsupported Django version')
class UrlsTestCase(TestCase):

    def setUp(self):

        class SampleView(View):
            def dispatch(self, request, *args, **kwargs):
                assert False, 'dispatch() should not be called'

        self.SampleView = SampleView

        def foo_view(request):
            assert False, 'view function should not be called'

        self.foo_view = foo_view

    def test_url(self):
        patterns = [
            url('s', self.SampleView.as_view(), name='sampleview'),
            url('f', self.foo_view, name='sampleview'),
        ]
        self.assertIsInstance(patterns[0], RegexURLPattern)
        self.assertIsInstance(patterns[1], RegexURLPattern)
        self.assertTrue(issubclass(self.SampleView, ExperimentsMixin))


@skipIf(DJANGO_VERSION < (1, 9), 'Unsupported Django version')
class ExperimentizeTestCase(TestCase):

    def setUp(self):

        class SampleView(View):
            def dispatch(self, request, *args, **kwargs):
                assert False, 'dispatch() should not be called'

        self.SampleView = SampleView

    def test_idempotence(self):
        experimentize(self.SampleView)
        experimentize(self.SampleView)
        experimentize(self.SampleView)
        self.assertTrue(issubclass(self.SampleView, ExperimentsMixin))
        subclasses = list(self.SampleView.__bases__)
        self.assertEqual(subclasses.count(ExperimentsMixin), 1)

    def test_applies_to_as_view(self):
        experimentize(self.SampleView.as_view())
        experimentize(self.SampleView)
        self.assertTrue(issubclass(self.SampleView, ExperimentsMixin))
        subclasses = list(self.SampleView.__bases__)
        self.assertEqual(subclasses.count(ExperimentsMixin), 1)
