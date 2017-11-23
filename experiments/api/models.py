# coding=utf-8
from datetime import timedelta
import logging
import random
from time import sleep
import uuid

from django.db import models
from django.db.models import Max
from django.db.utils import IntegrityError
from django.utils.encoding import python_2_unicode_compatible
import requests

from experiments.dateutils import now

from .. import conf


logger = logging.getLogger(__file__)


__all__ = (
    'DbLock',
    'RemoteExperiment',
)


CONTROL_STATE = 0
ENABLED_STATE = 1
TRACK_STATE = 3

STATES = (
    (CONTROL_STATE, 'Default/Control'),
    (ENABLED_STATE, 'Enabled'),
    (TRACK_STATE, 'Track'),
)


@python_2_unicode_compatible
class DbLock(models.Model):
    """Simple expirable lock, backed by database"""
    DEFAULT_TIMEOUT = 120  # 2 minutes
    RETRY_INTERVAL = 1  # 1 second
    name = models.SlugField(primary_key=True)
    uuid = models.CharField(
        max_length=36, null=False, unique=True, db_index=True,
        default=uuid.uuid4)
    expire_at = models.DateTimeField(null=False, db_index=True)

    def __str__(self):
        return self.name

    @classmethod
    def cleanup(cls):
        """Delete expired locks."""
        cls.objects.filter(expire_at__lte=now()).delete()

    def acquire(self, blocking=True, timeout=DEFAULT_TIMEOUT):
        """
        Acquire the lock.
        If acquired, lock will be auto-release after <timeout> seconds.
        If not acquired and <blocking>, will keep retrying every second
        for <timeout> seconds.
        """
        self.cleanup()
        expire_at = now() + timedelta(seconds=timeout)
        acquired = self._acquire(blocking, expire_at)
        if acquired:
            self.expire_at = now() + timedelta(seconds=timeout)
            self.save()
        return acquired

    def _acquire(self, blocking, expire_at):
        try:
            lock, acquired = DbLock.objects.get_or_create(
                name=self.name,
                defaults={'expire_at': expire_at},
            )
        except IntegrityError:
            acquired = False
            lock = None
        if acquired:
            self.uuid = lock.uuid
            return True
        if not blocking:
            return False
        while not acquired and now() < expire_at:
            sleep(self.RETRY_INTERVAL * random.uniform(0.75, 1.25))
            self.cleanup()
            acquired = self._acquire(False, expire_at)
        return acquired

    @property
    def _lock_query(self):
        return DbLock.objects.filter(
            name=self.name,
            uuid=self.uuid,
        )

    def reacquire(self, timeout=DEFAULT_TIMEOUT):
        """
        Extend validity of the lock by <timeout> seconds.
        Non-blocking.
        """
        self.cleanup()
        if not self._lock_query.exists():
            return False
        self.expire_at = now() + timedelta(seconds=timeout)
        self.save()
        return True

    def release(self):
        """Release the lock so that it may be acquired again."""
        count, _ = self._lock_query.delete()
        self.uuid = None
        return bool(count)


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
                relocked = lock.reacquire(timeout=60)
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
                'batch': batch,
            }
        )

    @classmethod
    def _cleanup(cls, batch):
        cls.objects.filter(batch__lt=batch).delete()
