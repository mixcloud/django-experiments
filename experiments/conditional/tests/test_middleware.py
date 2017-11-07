# coding=utf-8
from __future__ import absolute_import

from unittest import TestCase

from django.http import StreamingHttpResponse, HttpResponse, JsonResponse

try:
    from unittest import mock
except ImportError:
    import mock

from ..middleware import ExposeAutoEnrollMiddleware


class ExposeAutoEnrollMiddlewareTestCase(TestCase):

    def setUp(self):
        self.request = mock.MagicMock()
        self.response = mock.MagicMock()
        self.middleware = ExposeAutoEnrollMiddleware()

    def test_user_not_staff(self):
        self.request.user.is_staff = False
        with mock.patch.object(self.middleware, '_inject_json'):
            response = self.middleware.process_response(
                self.request, self.response)
            self.assertIs(response, self.response)
            self.middleware._inject_json.assert_not_called()

    def test_streaming_response_ignored(self):
        self.request.user.is_staff = True
        self.response = StreamingHttpResponse()
        with mock.patch.object(self.middleware, '_inject_json'):
            response = self.middleware.process_response(
                self.request, self.response)
            self.assertIs(response, self.response)
            self.middleware._inject_json.assert_not_called()

    def test_json_reponse_ignored(self):
        self.request.user.is_staff = True
        self.response = JsonResponse(
            data={"some": {'json': ['data', 'here']}}
        )
        with mock.patch.object(self.middleware, '_inject_json'):
            response = self.middleware.process_response(
                self.request, self.response)
            self.assertIs(response, self.response)
            self.middleware._inject_json.assert_not_called()

    def test_reponse_without_body_ignored(self):
        self.request.user.is_staff = True
        self.response = HttpResponse(
            b'<html><head></head><body>omg no closing tag!'
        )
        with mock.patch.object(self.middleware, '_inject_json'):
            response = self.middleware.process_response(
                self.request, self.response)
            self.assertIs(response, self.response)
            self.middleware._inject_json.assert_not_called()

    def test_request_has_no_experiments(self):
        self.request.user.is_staff = True
        self.response = HttpResponse(
            b'<html><head></head><body>gotalotofcontent</body></html>'
        )
        self.request.experiments = None
        with mock.patch.object(self.middleware, '_inject_json'):
            response = self.middleware.process_response(
                self.request, self.response)
            self.assertIs(response, self.response)
            self.middleware._inject_json.assert_not_called()

    def test_json_injected(self):
        self.request.user.is_staff = True
        self.response = HttpResponse(
            b'<html><head></head><body>gotalotofcontent</body></html>'
        )
        with mock.patch.object(self.middleware, '_inject_json'):
            response = self.middleware.process_response(
                self.request, self.response)
            self.assertIs(response, self.response)
            self.middleware._inject_json.assert_called_with(
                self.request.experiments, self.response)

    def test_inject_json(self):
        self.request.experiments.report = {'report': 'data'}
        self.response.content = (
            b'<html><head></head><body>gotalotofcontent</body></html>')
        self.middleware._inject_json(
            self.request.experiments, self.response)
        self.assertIn(b'{"report": "data"}', self.response.content)
