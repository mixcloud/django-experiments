import time

from django.db.models.signals import post_save, post_delete
from django.conf import settings
from django.core.signals import request_finished
from django.core.cache import cache

from experiments.models import Experiment

NoValue = object()

try:
    from celery.signals import task_postrun
except ImportError:  # celery must not be installed
    has_celery = False
else:
    has_celery = True


class ModelDict(object):
    """
    Dictionary-style access to a model. Populates a cache and a local in-memory
    store to avoid multiple hits to the database.

    Specifying ``instances=True`` will cause the cache to store instances
    rather than simple values.

    If ``auto_create=True`` accessing modeldict[key] when key does not exist
    will attempt to create it in the database.

    Functions in two different ways, depending on the constructor:

        # Given ``Model`` that has a column named ``foo``
        # where the value is "bar":

        mydict = ModelDict(Model, value='foo')
        mydict['test']
        >>> 'bar' #doctest: +SKIP

    If you want to use another key besides ``pk``, you may specify that in the
    constructor. However, this will be used as part of the cache key, so it's
    recommended to access it in the same way throughout your code.

        mydict = ModelDict(Model, key='foo', value='id')
        mydict['bar']
        >>> 'test' #doctest: +SKIP

    """
    def __init__(self, model, key='pk', value=None, instances=False,
                 auto_create=False, cache=cache, timeout=30, *args, **kwargs):
        assert value is not None

        cls_name = type(self).__name__
        model_name = model.__name__

        self._local_cache = None
        self._local_last_updated = None

        self._last_checked_for_remote_changes = None
        self.timeout = timeout

        self.remote_cache = cache
        self.remote_cache_key = cls_name
        self.remote_cache_last_updated_key = '%s.last_updated' % (cls_name,)

        self.key = key
        self.value = value

        self.model = model
        self.instances = instances
        self.auto_create = auto_create

        self.remote_cache_key = '%s:%s:%s' % (cls_name, model_name, self.key)
        self.remote_cache_last_updated_key = (
            '%s.last_updated:%s:%s' % (cls_name, model_name, self.key))

        request_finished.connect(self._cleanup)
        post_save.connect(self._post_save, sender=model)
        post_delete.connect(self._post_delete, sender=model)

        if has_celery:
            task_postrun.connect(self._cleanup)

    def __getitem__(self, key):
        self._populate()

        try:
            return self._local_cache[key]
        except KeyError:
            value = self.get_default(key)

            if value is NoValue:
                raise

            return value

    def __setitem__(self, key, value):
        if isinstance(value, self.model):
            value = getattr(value, self.value)

        manager = self.model._default_manager
        instance, created = manager.get_or_create(
            defaults={self.value: value},
            **{self.key: key}
        )

        # Ensure we're updating the value in the database if it changes
        if getattr(instance, self.value) != value:
            setattr(instance, self.value, value)
            manager.filter(**{self.key: key}).update(**{self.value: value})
            self._post_save(sender=self.model, instance=instance,
                            created=False)

    def __delitem__(self, key):
        self.model._default_manager.filter(**{self.key: key}).delete()
        # self._populate(reset=True)

    def __len__(self):
        if self._local_cache is None:
            self._populate()

        return len(self._local_cache)

    def __contains__(self, key):
        self._populate()
        return key in self._local_cache

    def __iter__(self):
        self._populate()
        return iter(self._local_cache)

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.model.__name__)

    def iteritems(self):
        self._populate()
        return self._local_cache.iteritems()

    def itervalues(self):
        self._populate()
        return self._local_cache.itervalues()

    def iterkeys(self):
        self._populate()
        return self._local_cache.iterkeys()

    def keys(self):
        return list(self.iterkeys())

    def values(self):
        return list(self.itervalues())

    def items(self):
        self._populate()
        return self._local_cache.items()

    def get(self, key, default=None):
        self._populate()
        return self._local_cache.get(key, default)

    def pop(self, key, default=NoValue):
        value = self.get(key, default)

        try:
            del self[key]
        except KeyError:
            pass

        return value

    def local_cache_has_expired(self):
        """
        Returns ``True`` if the in-memory cache has expired.
        """
        if not self._last_checked_for_remote_changes:
            return True  # Never checked before

        recheck_at = self._last_checked_for_remote_changes + self.timeout
        return time.time() > recheck_at

    def setdefault(self, key, value):
        if isinstance(value, self.model):
            value = getattr(value, self.value)

        instance, created = self.model._default_manager.get_or_create(
            defaults={self.value: value},
            **{self.key: key}
        )

    def get_default(self, key):
        if not self.auto_create:
            return NoValue
        result = self.model.objects.get_or_create(**{self.key: key})[0]
        if self.instances:
            return result
        return getattr(result, self.value)

    def local_cache_is_invalid(self):
        """
        Returns ``True`` if the local cache is invalid and needs to be
        refreshed with data from the remote cache.

        A return value of ``None`` signifies that no data was available.
        """
        # If the local_cache is empty, avoid hitting memcache entirely
        if self._local_cache is None:
            return True

        remote_last_updated = self.remote_cache.get(
            self.remote_cache_last_updated_key
        )

        if not remote_last_updated:
            # TODO: I don't like how we're overloading the return value here
            # for this method.  It would be better to have a separate method or
            # @property that is the remote last_updated value.
            return None  # Never been updated

        return int(remote_last_updated) > self._local_last_updated

    def get_cache_data(self):
        """
        Pulls data from the cache backend.
        """
        return self._get_cache_data()

    def clear_cache(self):
        """
        Clears the in-process cache.
        """
        self._local_cache = None
        self._local_last_updated = None
        self._last_checked_for_remote_changes = None

    def _populate(self, reset=False):
        """
        Ensures the cache is populated and still valid.

        The cache is checked when:

        - The local timeout has been reached
        - The local cache is not set

        The cache is invalid when:

        - The global cache has expired (via remote_cache_last_updated_key)
        """
        now = int(time.time())

        # If asked to reset, then simply set local cache to None
        if reset:
            self._local_cache = None
        # Otherwise, if the local cache has expired, we need to go check with
        # our remote last_updated value to see if the dict values have changed.
        elif self.local_cache_has_expired():

            local_cache_is_invalid = self.local_cache_is_invalid()

            # If local_cache_is_invalid  is None, that means that there was no
            # data present, so we assume we need to add the key to cache.
            if local_cache_is_invalid is None:
                self.remote_cache.add(self.remote_cache_last_updated_key, now)

            # Now, if the remote has changed OR it was None in the first place,
            # pull in the values from the remote cache and set it to the
            # local_cache
            if local_cache_is_invalid or local_cache_is_invalid is None:
                self._local_cache = self.remote_cache.get(
                    self.remote_cache_key)

            # No matter what, we've updated from remote, so mark ourselves as
            # such so that we won't expire until the next timeout
            self._local_last_updated = now

        # Update from cache if local_cache is still empty
        if self._local_cache is None:
            self._update_cache_data()

        # No matter what happened, we last checked for remote changes just now
        self._last_checked_for_remote_changes = now

        return self._local_cache

    def _update_cache_data(self):
        self._local_cache = self.get_cache_data()

        now = int(time.time())
        self._local_last_updated = now
        self._last_checked_for_remote_changes = now

        # We only set remote_cache_last_updated_key when we know the cache is
        # current because setting this will force all clients to invalidate
        # their cached data if it's newer
        self.remote_cache.set(self.remote_cache_key, self._local_cache)
        self.remote_cache.set(
            self.remote_cache_last_updated_key,
            self._last_checked_for_remote_changes
        )

    def _cleanup(self, *args, **kwargs):
        # We set _last_updated to a false value to ensure we hit the
        # last_updated cache on the next request
        self._last_checked_for_remote_changes = None

    def _get_cache_data(self):
        qs = self.model._default_manager
        if self.instances:
            return dict((getattr(i, self.key), i) for i in qs.all())
        return dict(qs.values_list(self.key, self.value))

    # Signals

    def _post_save(self, sender, instance, created, **kwargs):
        self._populate(reset=True)

    def _post_delete(self, sender, instance, **kwargs):
        self._populate(reset=True)


experiment_manager = ModelDict(
    Experiment, key='name', value='value', instances=True,
    auto_create=getattr(settings, 'EXPERIMENTS_AUTO_CREATE', True))
