# coding=utf-8
import json

try:
    # for Django >= 1.10
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    # for Django < 1.10
    MiddlewareMixin = object


class ExposeAutoEnrollMiddleware(MiddlewareMixin):
    """
    Set a cookie that can be read on FE to determine whether an
    experiment is active on any page.
    TODO: make a JS indicator for staff users
    """
    def process_response(self, request, response):
        if not request.user.is_staff:
            return response
        content = getattr(response, 'content', None)
        if content is None or b'</body>' not in content:
            return response
        experiments = getattr(request, 'experiments', None)
        if experiments is None:
            return response
        self._inject_json(experiments, response)
        return response

    def _inject_json(self, experiments, response):
        report = json.dumps(experiments.report)
        script = '<script>window.ca_experiments = {};</script>'.format(
            report,
        ).encode('utf-8')
        response.content = response.content.replace(
            b'</body>', script + b'</body>')
