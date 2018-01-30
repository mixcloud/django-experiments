# coding=utf-8
import logging

from django.db import models
from django.db.models import Max
from jsonfield import JSONField
import requests

from .. import conf
from ..consts import STATES
from ..lock import DbLock as Lock


logger = logging.getLogger(__file__)


__all__ = (
    'RemoteExperiment',
    'RemoteApiException',
)


class RemoteApiException(Exception):
    """
    Wrapper used to wrap any other exception that might occur while
    syncing RemoteExperiment instances with remote APIs.
    This exception is recognised in django admin (custom code),
    and displayed in standard messages.
    """
    def __init__(self, server, original_exception):
        self.server = server
        self.original_exception = original_exception

    def __repr__(self):
        return 'RemoteApiException({})'.format(repr(self.original_exception))


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

    MAX_WAIT_REMOTE_SYNC = 60  # seconds

    class Meta:
        ordering = ('-start_date', 'name',)

    @classmethod
    def update_remotes(cls):
        """
        Looks up all remote APIs and updates local instances.
        Makes sure that only one lookup is running at a time.
        Yields any exceptions so that they can be displayed in
        the admin as messages.
        """
        lock = Lock('fetching_remote_experiments')
        try:
            if lock.acquire(blocking=False):
                exceptions = cls._update_remotes(lock)
                for e in exceptions:
                    yield e
            else:
                # just wait for another thread or process to finish the work:
                lock.acquire(blocking=True)
        finally:
            lock.release()

    @classmethod
    def _update_remotes(cls, lock):
        """
        Goes over the list of remote servers, fetches data from
        each one, and updates local DB.
        """
        batch = RemoteExperiment.objects.all().aggregate(
            Max('batch'))['batch__max'] or 0
        batch += 1
        for server in conf.API['remotes']:
            try:
                relocked = lock.extend(timeout=cls.MAX_WAIT_REMOTE_SYNC)
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
        """
        Reads the list of experiments from an API endpoint,
        taking care of pagination.
        """
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
        """Makes an actual request to remote API"""
        headers = {
            'Authorization': 'Token {}'.format(token),
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache',
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    @classmethod
    def _update_or_create(cls, remote_instance, remote_site, batch):
        """Create instances in local DB from remote API data"""
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
        """Deletes all previous batches"""
        cls.objects.filter(batch__lt=batch).delete()

    @property
    def remote_payload(self):
        """
        Payload used for PATCH requests to change experiment state remotely
        """
        return {
            'state': self.state,
        }

    @property
    def remote_token(self):
        """
        Token from `EXPERIMENTS_API` settings for site that
        is the origin of this instance.
        """
        for server in conf.API['remotes']:
            if self.url.startswith(server['url']):
                return server['token']
