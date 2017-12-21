# coding=utf-8
from test import lock_tests
from unittest import skipIf

from django.conf import settings

from experiments.models import DbLock


@skipIf('sqlite' in settings.DATABASES['default']['ENGINE'],
        'Not testing DbLock with SQLite')
class DbLockTestCase(lock_tests.LockTests):

    def locktype(self):
        return DbLock('foo')

    def test_extend(self):
        lock = self.locktype()
        lock.acquire()
        self.assertTrue(lock.extend())
        lock.release()
        self.assertFalse(lock.extend())
        del lock

    def test_extend_expired(self):
        lock = self.locktype()
        lock.acquire()
        self.assertTrue(lock.extend(0))
        self.assertFalse(lock.extend())
        del lock
