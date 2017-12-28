# coding=utf-8
from datetime import timedelta
import logging
import random
from time import sleep
import uuid

import django
from django.db import models, transaction
from django.db.utils import IntegrityError, OperationalError
from django.utils.encoding import python_2_unicode_compatible

from experiments.dateutils import now


logger = logging.getLogger(__file__)
TIMEOUT_MAX = 9223372036.0


@python_2_unicode_compatible
class DbLock(models.Model):
    """Simple expirable lock, backed by database"""
    DEFAULT_TIMEOUT = 5  # seconds
    RETRY_INTERVAL = 1  # seconds
    DB_ERROR_RETRY_INTERVAL = 0.1  # seconds
    name = models.SlugField(primary_key=True)
    uuid = models.CharField(
        max_length=36, null=False, unique=True, db_index=True,
        default=uuid.uuid4)
    expire_at = models.DateTimeField(null=False, db_index=True)

    def __str__(self):
        return '<{state} {name} object at {uuid}>'.format(
            state='locked' if self.locked() else 'unlocked',
            name=self.name,
            uuid=self.uuid,
        )

    @transaction.atomic
    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.uuid:
            self.uuid = uuid.uuid4()
        super(DbLock, self).save(
            force_insert, force_update, using, update_fields)

    @classmethod
    def cleanup(cls):
        """Delete expired locks."""
        try:
            cls.objects.filter(expire_at__lte=now()).delete()
        except OperationalError:
            pass

    def acquire(self, blocking=True, timeout=None):
        """
        Acquire the lock.
        If acquired, lock will be auto-release after <timeout> seconds.
        If not acquired and <blocking>, will keep retrying every second
        for <timeout> seconds.
        """
        if not blocking and timeout is not None:
            raise ValueError('Cannot set timeout if not blocking')
        timeout = self.DEFAULT_TIMEOUT if timeout is None else timeout
        if timeout < 0:
            raise ValueError('Cannot set negative timeout')
        if timeout > TIMEOUT_MAX:
            raise OverflowError('Timeout too large')
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
        except (IntegrityError, OperationalError):
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

    def extend(self, timeout=DEFAULT_TIMEOUT):
        """
        Extend validity of the lock by <timeout> seconds.
        Non-blocking.
        """
        if not self.locked():
            return False
        self.expire_at = now() + timedelta(seconds=timeout)
        self.save()
        return True

    def locked(self):
        self.cleanup()
        return self._lock_query.exists()

    def release(self):
        """Release the lock so that it may be acquired again."""
        limit = 10
        for i in range(limit):
            try:
                return self._release()
            except OperationalError:
                if i == limit-1:
                    raise
                sleep(self.DB_ERROR_RETRY_INTERVAL * random.uniform(0.3, 1.6))

    def _release(self):
        if django.VERSION < (1, 9):
            count = self._lock_query.count()
            self._lock_query.delete()
        else:
            count, _ = self._lock_query.delete()
        self.uuid = None
        return bool(count)

    def __del__(self):
        self.release()

    def __enter__(self):
        self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
