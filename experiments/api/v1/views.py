# coding=utf-8
import logging

from django.http import HttpResponseNotAllowed, HttpResponse
from rest_framework.authentication import (
    TokenAuthentication,
    SessionAuthentication,
)
from rest_framework.generics import (
    ListAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.status import HTTP_204_NO_CONTENT, HTTP_403_FORBIDDEN
from rest_framework.views import (
    APIView,
)

from ... import conf
from ...models import Experiment
from .paginators import DefaultPaginator
from .serializers import (
    ExperimentNestedSerializer,
    ExperimentSerializer,
    SiteSerializer,
)

logger = logging.getLogger(__file__)


class APIRootView(APIView):
    permission_classes = []

    def get(self, request):
        data = SiteSerializer().data

        if 'server' in conf.API['api_mode']:
            data['experiments'] = reverse(
                'experiments:api:v1:experiments', request=request)
        return Response(data)


class AuthMixin(object):
    authentication_classes = (TokenAuthentication, SessionAuthentication,)
    permission_classes = (IsAdminUser,)

    def dispatch(self, request, *args, **kwargs):
        if 'server' not in conf.API['api_mode']:
            return HttpResponse(status=HTTP_403_FORBIDDEN)
        return super(AuthMixin, self).dispatch(request, *args, **kwargs)


class ExperimentsListView(AuthMixin, ListAPIView):
    pagination_class = DefaultPaginator
    queryset = Experiment.objects.all()
    serializer_class = ExperimentNestedSerializer


class ExperimentView(AuthMixin, RetrieveUpdateAPIView):
    queryset = Experiment.objects.all()
    lookup_field = 'name'
    lookup_url_kwarg = 'name'
    serializer_class = ExperimentSerializer
