# coding=utf-8

try:
    from unittest import mock, skip
except ImportError:
    import mock


class DummyLockTests(object):

    @classmethod
    def new(cls):
        test_class = cls
        return skip(test_class)
