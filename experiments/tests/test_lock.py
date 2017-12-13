from test import lock_tests

from experiments.api.models import DbLock


class DbLockTestCase(lock_tests.LockTests):

    @staticmethod
    def locktype():
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
