import redis

from app.config import REDIS_URL

redis_client = redis.from_url(REDIS_URL, decode_responses=True)
