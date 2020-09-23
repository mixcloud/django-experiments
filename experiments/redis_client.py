from django.conf import settings
import redis
from redis.sentinel import Sentinel

def get_redis_client():
    if getattr(settings, 'EXPERIMENTS_REDIS_SENTINELS', None):
        sentinel = Sentinel(settings.EXPERIMENTS_REDIS_SENTINELS, socket_timeout=settings.EXPERIMENTS_REDIS_SENTINELS_TIMEOUT)
        host, port = sentinel.discover_master(settings.EXPERIMENTS_REDIS_MASTER_NAME)
    else:
        host = getattr(settings, 'EXPERIMENTS_REDIS_HOST', 'localhost')
        port = getattr(settings, 'EXPERIMENTS_REDIS_PORT', 6379)

    password = getattr(settings, 'EXPERIMENTS_REDIS_PASSWORD', None)
    db = getattr(settings, 'EXPERIMENTS_REDIS_DB', 0)

    return redis.Redis(host=host, port=port, password=password, db=db, charset="utf-8", decode_responses=True)
