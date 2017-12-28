# coding=utf-8
from django.contrib.admin.utils import quote
from rest_framework import serializers
from rest_framework.reverse import reverse

from ... import conf
from ..models import RemoteExperiment
from ...admin_utils import get_experiment_stats
from ...models import Experiment


class ReadOnlyMixin(object):
    def __init__(self, **kwargs):
        kwargs['read_only'] = True
        super(ReadOnlyMixin, self).__init__(**kwargs)


class RemoteAdminUrl(ReadOnlyMixin, serializers.URLField):

    def to_representation(self, value):
        request = self.context.get('request', None)
        url = reverse(
            'admin:experiments_experiment_change',
            args=(quote(value.name),),
            request=request)
        return url


class ExperimentUrlField(ReadOnlyMixin, serializers.URLField):
    def __init__(self, **kwargs):
        kwargs['source'] = 'name'
        super(ExperimentUrlField, self).__init__(**kwargs)

    def to_representation(self, value):
        request = self.context.get('request', None)
        return reverse(
            'experiments:api:v1:experiment',
            request=request,
            kwargs={'name': value})


class SiteSerializer(ReadOnlyMixin, serializers.Serializer):

    def to_representation(self, instance):
        return self.get_initial()

    def get_initial(self):
        return {'name': conf.API['local']['name']}


class ExperimentSerializer(serializers.ModelSerializer):
    url = ExperimentUrlField()
    admin_url = RemoteAdminUrl(source='*')
    site = SiteSerializer(source='*')
    statistics = serializers.SerializerMethodField()

    lookup_field = 'name'
    lookup_url_kwarg = 'name'

    class Meta:
        model = Experiment
        fields = (
            'url',
            'admin_url',
            'name',
            'description',
            'alternatives',
            'state',
            'start_date',
            'end_date',
            'statistics',
            'site',
        )
        read_only_fields = (
            'url',
            'name',
            'description',
            'alternatives',
            'start_date',
            'end_date',
        )

    def get_statistics(self, obj):
        stats = get_experiment_stats(obj)
        stats['results'] = {
            alternative: data
            for alternative, data in stats['results'].items()
            if data['relevant']
        }
        return stats


class ExperimentNestedSerializer(ExperimentSerializer):
    alternatives_list = serializers.SerializerMethodField()

    class Meta(ExperimentSerializer.Meta):
        fields = (
            'url',
            'admin_url',
            'name',
            'state',
            'start_date',
            'end_date',
            'alternatives_list',
            'statistics',
        )
        read_only_fields = (
            'url',
            'name',
            'state',
            'start_date',
            'end_date',
        )

    def get_alternatives_list(self, obj):
        return list(obj.alternatives.keys())


class RemoteExperimentStateSerializer(serializers.ModelSerializer):

    class Meta:
        model = RemoteExperiment
        fields = ('state',)
