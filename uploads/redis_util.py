# redis_util.py

import redis
from django.conf import settings

def get_redis_connection():
    redis_host, redis_port = settings.CHANNEL_LAYERS['default']['CONFIG']['hosts'][0]
    return redis.Redis(host=redis_host, port=redis_port)

# Initialize a single Redis connection that can be reused
redis_connection = get_redis_connection()
