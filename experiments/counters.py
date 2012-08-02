from django.conf import settings

import redis
from redis.exceptions import ConnectionError, ResponseError

REDIS_HOST = getattr(settings, 'EXPERIMENTS_REDIS_HOST', 'localhost')
REDIS_PORT = getattr(settings, 'EXPERIMENTS_REDIS_PORT', 6379)
REDIS_EXPERIMENTS_DB = getattr(settings, 'EXPERIMENTS_REDIS_DB', 0)

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_EXPERIMENTS_DB)

COUNTER_CACHE_KEY = 'experiments:%s'

def counter_increment(key, increment=1):
    try:
        cache_key = COUNTER_CACHE_KEY % key
        r.incr(cache_key, increment)
        return int(r.get(cache_key))
    except (ConnectionError, ResponseError):
        # Handle Redis failures gracefully
        pass

def counter_get(key):
    try:
        cache_key = COUNTER_CACHE_KEY % key
        count = r.get(cache_key)
    except (ConnectionError, ResponseError):
        # Handle Redis failures gracefully
        return 0
    if not count:
        return 0
    return int(count)

def counter_reset(key):
    try:
        cache_key = COUNTER_CACHE_KEY % key
        return r.delete(cache_key)
    except (ConnectionError, ResponseError):
        # Handle Redis failures gracefully
        return False

def counter_reset_pattern(key):
    #similar to above, but can pass pattern as arg instead
    try:
        cache_key = COUNTER_CACHE_KEY % key
        for key in r.keys(cache_key):
            r.delete(key)
        return True
    except (ConnectionError, ResponseError):
        # Handle Redis failures gracefully
        return False