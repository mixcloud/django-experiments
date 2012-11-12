from django.conf import settings

import redis
from redis.exceptions import ConnectionError, ResponseError

REDIS_HOST = getattr(settings, 'EXPERIMENTS_REDIS_HOST', 'localhost')
REDIS_PORT = getattr(settings, 'EXPERIMENTS_REDIS_PORT', 6379)
REDIS_PASSWORD = getattr(settings, 'EXPERIMENTS_REDIS_PASSWORD', None)
REDIS_EXPERIMENTS_DB = getattr(settings, 'EXPERIMENTS_REDIS_DB', 0)

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, db=REDIS_EXPERIMENTS_DB)

COUNTER_CACHE_KEY = 'experiments:participants:%s'
COUNTER_FREQ_CACHE_KEY = 'experiments:freq:%s'

def increment(key, participant_identifier):
    try:
        cache_key = COUNTER_CACHE_KEY % key
        freq_cache_key = COUNTER_FREQ_CACHE_KEY % key
        new_value = r.hincrby(cache_key, participant_identifier, 1)

        # Maintain histogram of per-user counts
        if new_value > 1:
            r.hincrby(freq_cache_key, new_value - 1, -1)
        r.hincrby(freq_cache_key, new_value, 1)
    except (ConnectionError, ResponseError):
        # Handle Redis failures gracefully
        pass

def get(key):
    try:
        cache_key = COUNTER_CACHE_KEY % key
        return r.hlen(cache_key)
    except (ConnectionError, ResponseError):
        # Handle Redis failures gracefully
        return 0


def get_frequencies(key):
    try:
        freq_cache_key = COUNTER_FREQ_CACHE_KEY % key
        # In some cases when there are concurrent updates going on, there can
        # briefly be a negative result for some frequency count. We discard these
        # as they shouldn't really affect the result, and they are about to become
        # zero anyway.
        return dict((int(k),int(v)) for (k,v) in r.hgetall(freq_cache_key).items() if int(v) > 0)
    except (ConnectionError, ResponseError):
        # Handle Redis failures gracefully
        return tuple()

def reset(key):
    try:
        cache_key = COUNTER_CACHE_KEY % key
        r.delete(cache_key)
        freq_cache_key = COUNTER_FREQ_CACHE_KEY % key
        r.delete(freq_cache_key)
        return True
    except (ConnectionError, ResponseError):
        # Handle Redis failures gracefully
        return False

def reset_pattern(key):
    #similar to above, but can pass pattern as arg instead
    try:
        cache_key = COUNTER_CACHE_KEY % key
        for key in r.keys(cache_key):
            r.delete(key)
        freq_cache_key = COUNTER_FREQ_CACHE_KEY % key
        for key in r.keys(freq_cache_key):
            r.delete(key)
        return True
    except (ConnectionError, ResponseError):
        # Handle Redis failures gracefully
        return False
