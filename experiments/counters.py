from django.conf import settings

import redis
from redis.exceptions import ConnectionError, ResponseError

REDIS_HOST = getattr(settings, 'EXPERIMENTS_REDIS_HOST', 'localhost')
REDIS_PORT = getattr(settings, 'EXPERIMENTS_REDIS_PORT', 6379)
REDIS_EXPERIMENTS_DB = getattr(settings, 'EXPERIMENTS_REDIS_DB', 0)

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_EXPERIMENTS_DB)

COUNTER_CACHE_KEY = 'experiments:%s'

def increment(key, participant_identifier):
    try:
        cache_key = COUNTER_CACHE_KEY % key
        r.sadd(cache_key, participant_identifier)
    except (ConnectionError, ResponseError):
        # Handle Redis failures gracefully
        pass

def get(key):
    try:
        cache_key = COUNTER_CACHE_KEY % key
        return r.scard(cache_key)
    except (ConnectionError, ResponseError):
        # Handle Redis failures gracefully
        return 0

def reset(key):
    try:
        cache_key = COUNTER_CACHE_KEY % key
        return r.delete(cache_key)
    except (ConnectionError, ResponseError):
        # Handle Redis failures gracefully
        return False

def reset_pattern(key):
    #similar to above, but can pass pattern as arg instead
    try:
        cache_key = COUNTER_CACHE_KEY % key
        for key in r.keys(cache_key):
            r.delete(key)
        return True
    except (ConnectionError, ResponseError):
        # Handle Redis failures gracefully
        return False
