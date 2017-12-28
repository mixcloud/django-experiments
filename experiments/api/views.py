# coding=utf-8
from collections import OrderedDict

from django.test import override_settings
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView


class APIVersionsView(APIView):
    """
    Experiments API root.
    There might be multiple active versions of the API. All active versions are
    listed here.
    """
    permission_classes = []

    def get(self, request):
        data = OrderedDict()
        data['versions'] = OrderedDict((
            ('1.0', reverse('experiments:api:v1:root', request=request)),
        ))
        return Response(data)
