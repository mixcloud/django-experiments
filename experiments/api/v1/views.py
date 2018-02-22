# coding=utf-8
import logging

import requests
from django.http import HttpResponse
from rest_framework.authentication import (
    TokenAuthentication,
    SessionAuthentication,
)
from rest_framework.exceptions import APIException
from rest_framework.generics import (
    ListAPIView,
    RetrieveUpdateAPIView,
    GenericAPIView,
)
from rest_framework.mixins import UpdateModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.status import HTTP_403_FORBIDDEN
from rest_framework.views import APIView

from ... import conf
from ...models import Experiment
from ..models import RemoteExperiment
from .paginators import DefaultPaginator
from .serializers import (
    ExperimentNestedSerializer,
    ExperimentSerializer,
    SiteSerializer,
    RemoteExperimentStateSerializer,
)

logger = logging.getLogger(__file__)


class APIRootView(APIView):
    permission_classes = []

    def get(self, request):
        data = SiteSerializer().data

        if 'server' in conf.API['api_mode']:
            data['experiments'] = reverse(
                'experiments:api:v1:experiments', request=request)
        if 'client' in conf.API['api_mode']:
            data['remote_experiments'] = reverse(
                'experiments:api:v1:remote_experiments', request=request)
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


class RemoteExperimentView(AuthMixin, APIView):
    """
    ## Remote Experiment proxy

    This part of the API updates locally stored `RemoteExperiment`
    models, but vefore save each update is pushed to the remote API
    from where the `RemoteExperiment` instance originated.

    To toggle experiment state, go to
    [/experiments/api/v1/remote_experiment/EXPERIMENT_ID/toggle/](./EXPERIMENT_ID/toggle/)
    endpoint.
    Replace `EXPERIMENT_ID` with id of the local `RemoteExperiment` instance.
    """


class RemoteExperimentStateView(AuthMixin, RetrieveUpdateAPIView):
    """
    This endpoint acts as a proxy between admin jQuery code and
    an ExperimentView API endpoint on a remote site.
    """
    queryset = RemoteExperiment.objects.all()
    serializer_class = RemoteExperimentStateSerializer

    def perform_update(self, serializer):
        """
        Performs the intended action. Request data has been
        validated at this point.

        Before updating the local DB instance (the usual action),
        we need to update the remote instance as well, and then
        only then we update the local data accordingly to avoid
        inconsistencies.
        """
        serializer.save()  # needed at this point because serializer internals
        try:
            remote_data = self._remote_patch(
                serializer.instance, serializer.data)
        except Exception as e:
            raise APIException(repr(e))
        self._check_response(remote_data, serializer.instance)

    def _remote_patch(self, instance, data):
        """Issues the actual HTTP request"""
        headers = {
            'Authorization': 'Token {}'.format(instance.remote_token)
        }
        response = requests.patch(
            instance.url,
            data,
            headers=headers,
        )
        response.raise_for_status()
        return response.json()

    def _check_response(self, remote_data, instance):
        """
        Compares returned data to local and update if needed.
        The update should happen only in case of errors, because
        `serializer.save()` has already been called.
        """
        remote_state = remote_data['state']
        if remote_state != instance.state:
            self.queryset.filter(id=instance.id).update(state=remote_state)
