import json
from typing import Optional, Any, Dict
import redis
from app.config import settings

# Parse from full REDIS_URL
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

# Cache TTL (seconds)
SUBSCRIPTION_CACHE_TTL = 3600

def get_subscription_cache_key(subscription_id: str) -> str:
    return f"subscription:{subscription_id}"

def cache_subscription(subscription_id: str, subscription_data: Dict[str, Any]) -> None:
    """Cache subscription data"""
    key = get_subscription_cache_key(subscription_id)
    redis_client.setex(key, SUBSCRIPTION_CACHE_TTL, json.dumps(subscription_data))

def get_cached_subscription(subscription_id: str) -> Optional[Dict[str, Any]]:
    """Get subscription data from cache"""
    key = get_subscription_cache_key(subscription_id)
    data = redis_client.get(key)
    if data:
        return json.loads(data)
    return None

def invalidate_subscription_cache(subscription_id: str) -> None:
    """Invalidate subscription cache"""
    key = get_subscription_cache_key(subscription_id)
    redis_client.delete(key)

def is_redis_available() -> bool:
    """Check Redis connectivity"""
    try:
        return redis_client.ping()
    except Exception:
        return False
