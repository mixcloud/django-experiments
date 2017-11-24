from test import lock_tests

from experiments.api.models import DbLock


class DbLockTestCase(lock_tests.LockTests):

    @staticmethod
    def locktype():
        return DbLock('foo')

    def test_reacquire(self):
        lock = self.locktype()
        lock.acquire()
        self.assertTrue(lock.reacquire())
        lock.release()
        self.assertFalse(lock.reacquire())
        del lock

    def test_reacquire_expired(self):
        lock = self.locktype()
        lock.acquire()
        self.assertTrue(lock.reacquire(0))
        self.assertFalse(lock.reacquire())
        del lock
