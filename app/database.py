import redis

from app.config import REDIS_URL

redis_client: redis.Redis = redis.from_url(  # type: ignore[assignment]
    REDIS_URL, decode_responses=True
)
