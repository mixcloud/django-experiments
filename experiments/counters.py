from django.conf import settings

import redis
from redis.sentinel import Sentinel
from redis.exceptions import ConnectionError, ResponseError


COUNTER_CACHE_KEY = 'experiments:participants:%s'
COUNTER_FREQ_CACHE_KEY = 'experiments:freq:%s'


class Counters(object):
    def __init__(self):
        if getattr(settings, 'EXPERIMENTS_REDIS_SENTINELS', None):
            sentinel = Sentinel(settings.EXPERIMENTS_REDIS_SENTINELS)
            host, port = sentinel.discover_master(settings.EXPERIMENTS_REDIS_MASTER_NAME)
        else:
            host = getattr(settings, 'EXPERIMENTS_REDIS_HOST', 'localhost')
            port = getattr(settings, 'EXPERIMENTS_REDIS_PORT', 6379)

        password = getattr(settings, 'EXPERIMENTS_REDIS_PASSWORD', None)
        db = getattr(settings, 'EXPERIMENTS_REDIS_DB', 0)

        self.redis = redis.Redis(host=host, port=port, password=password, db=db)

    def increment(self, key, participant_identifier, count=1):
        if count == 0:
            return

        try:
            cache_key = COUNTER_CACHE_KEY % key
            freq_cache_key = COUNTER_FREQ_CACHE_KEY % key
            new_value = self.redis.hincrby(cache_key, participant_identifier, count)

            # Maintain histogram of per-user counts
            if new_value > count:
                self.redis.hincrby(freq_cache_key, new_value - count, -1)
            self.redis.hincrby(freq_cache_key, new_value, 1)
        except (ConnectionError, ResponseError):
            # Handle Redis failures gracefully
            pass

    def clear(self, key, participant_identifier):
        try:
            # Remove the direct entry
            cache_key = COUNTER_CACHE_KEY % key
            pipe = self.redis.pipeline()
            freq, _ = pipe.hget(cache_key, participant_identifier).hdel(cache_key, participant_identifier).execute()

            # Remove from the histogram
            freq_cache_key = COUNTER_FREQ_CACHE_KEY % key
            self.redis.hincrby(freq_cache_key, freq, -1)
        except (ConnectionError, ResponseError):
            # Handle Redis failures gracefully
            pass

    def get(self, key):
        try:
            cache_key = COUNTER_CACHE_KEY % key
            return self.redis.hlen(cache_key)
        except (ConnectionError, ResponseError):
            # Handle Redis failures gracefully
            return 0

    def get_frequency(self, key, participant_identifier):
        try:
            cache_key = COUNTER_CACHE_KEY % key
            freq = self.redis.hget(cache_key, participant_identifier)
            return int(freq) if freq else 0
        except (ConnectionError, ResponseError):
            # Handle Redis failures gracefully
            return 0

    def get_frequencies(self, key):
        try:
            freq_cache_key = COUNTER_FREQ_CACHE_KEY % key
            # In some cases when there are concurrent updates going on, there can
            # briefly be a negative result for some frequency count. We discard these
            # as they shouldn't really affect the result, and they are about to become
            # zero anyway.
            return dict((int(k), int(v)) for (k, v) in self.redis.hgetall(freq_cache_key).items() if int(v) > 0)
        except (ConnectionError, ResponseError):
            # Handle Redis failures gracefully
            return tuple()

    def reset(self, key):
        try:
            cache_key = COUNTER_CACHE_KEY % key
            self.redis.delete(cache_key)
            freq_cache_key = COUNTER_FREQ_CACHE_KEY % key
            self.redis.delete(freq_cache_key)
            return True
        except (ConnectionError, ResponseError):
            # Handle Redis failures gracefully
            return False

    def reset_pattern(self, pattern_key):
        #similar to above, but can pass pattern as arg instead
        try:
            cache_key = COUNTER_CACHE_KEY % pattern_key
            for key in self.redis.keys(cache_key):
                self.redis.delete(key)
            freq_cache_key = COUNTER_FREQ_CACHE_KEY % pattern_key
            for key in self.redis.keys(freq_cache_key):
                self.redis.delete(key)
            return True
        except (ConnectionError, ResponseError):
            # Handle Redis failures gracefully
            return False
