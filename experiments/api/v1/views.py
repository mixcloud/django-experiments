# coding=utf-8
import logging

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
from rest_framework.views import (
    APIView,
)

from ...models import Experiment
from .paginators import DefaultPaginator
from .serializers import (
    ExperimentNestedSerializer,
    ExperimentSerializer,
    SiteSerializer,
)

logger = logging.getLogger(__file__)


class APIRootView(APIView):

    def get(self, request):
        data = SiteSerializer().data
        data['experiments'] = reverse(
            'experiments_api:v1:experiments', request=request)
        return Response(data)


class AuthMixin(object):
    authentication_classes = (TokenAuthentication, SessionAuthentication,)
    permission_classes = (IsAdminUser,)


class ExperimentsListView(AuthMixin, ListAPIView):
    pagination_class = DefaultPaginator
    queryset = Experiment.objects.all()
    serializer_class = ExperimentNestedSerializer


class ExperimentView(AuthMixin, RetrieveUpdateAPIView):
    queryset = Experiment.objects.all()
    lookup_field = 'name'
    lookup_url_kwarg = 'name'
    serializer_class = ExperimentSerializer
