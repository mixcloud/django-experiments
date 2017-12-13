# coding=utf-8
import logging

from django.db import models
from django.db.models import Max
from jsonfield import JSONField
import requests

from .. import conf
from ..consts import STATES
from ..lock import DbLock


logger = logging.getLogger(__file__)


__all__ = (
    'RemoteExperiment',
)


class RemoteApiException(Exception):
    def __init__(self, server, original_exception):
        self.server = server
        self.original_exception = original_exception


class RemoteExperiment(models.Model):
    site = models.CharField(
        max_length=150, null=False, blank=False, default='', editable=False)
    name = models.CharField(
        max_length=150, null=False, blank=False, default='', editable=False)
    url = models.URLField(
        max_length=150, null=False, blank=False, default='', editable=False)
    admin_url = models.URLField(
        max_length=150, null=False, blank=False, default='', editable=False)
    state = models.IntegerField(choices=STATES)
    start_date = models.DateTimeField(null=True, editable=False)
    end_date = models.DateTimeField(null=True, editable=False)
    alternatives_list = JSONField(default={}, null=False, editable=False)
    statistics = JSONField(default={}, null=False, editable=False)
    batch = models.PositiveIntegerField(
        default=0, null=False, editable=False)

    class Meta:
        ordering = ('-start_date', 'name',)

    @classmethod
    def update_remotes(cls):
        lock = DbLock('fetching_remote_experiments')
        try:
            if lock.acquire(blocking=False):
                excs = cls._update_remotes(lock)
                for e in excs:
                    yield e
            else:
                # just wait for another thread or process to finish the work:
                lock.acquire(blocking=True)
        finally:
            lock.release()

    @classmethod
    def _update_remotes(cls, lock):
        batch = RemoteExperiment.objects.all().aggregate(
            Max('batch'))['batch__max'] or 0
        batch += 1
        for server in conf.API['remotes']:
            try:
                relocked = lock.extend(timeout=60)
                if not relocked:
                    logger.warning(
                        'Server too slow or lock to short! {}'.format(server))
                for instance, site in cls._fetch_remote_instances(server):
                    cls._update_or_create(instance, site, batch)
                cls._cleanup(batch)
            except Exception as e:
                logger.exception('Failed updating from remote experiments API')
                yield RemoteApiException(original_exception=e, server=server)

    @classmethod
    def _fetch_remote_instances(cls, server):
        url = '{}/experiments/api/v1/experiment/'.format(server['url'])
        token = server['token']
        while url:
            response = cls._fetch_paginated_page(url, token)
            site = response['site']
            for remote_experiment in response['results']:
                yield remote_experiment, site
            url = response['next']

    @classmethod
    def _fetch_paginated_page(cls, url, token):
        headers = {
            'Authorization': 'Token {}'.format(token),
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache',
        }
        return requests.get(url, headers=headers).json()

    @classmethod
    def _update_or_create(cls, remote_instance, remote_site, batch):
        local_instance, _ = cls.objects.update_or_create(
            site=remote_site['name'],
            name=remote_instance['name'],
            defaults={
                'url': remote_instance['url'],
                'admin_url': remote_instance['admin_url'],
                'start_date': remote_instance['start_date'],
                'end_date': remote_instance['end_date'],
                'state': remote_instance['state'],
                'statistics': remote_instance['statistics'],
                'alternatives_list': remote_instance['alternatives_list'],
                'batch': batch,
            }
        )

    @classmethod
    def _cleanup(cls, batch):
        cls.objects.filter(batch__lt=batch).delete()
