import redis
import json
from typing import Optional
from config import settings

redis_client = redis.from_url(settings.redis_url, decode_responses=True)

def cache_get(key: str) -> Optional[dict]:
    """Get value from cache"""
    try:
        value = redis_client.get(key)
        return json.loads(value) if value else None
    except Exception:
        return None

def cache_set(key: str, value: dict, ttl: int = None):
    """Set value in cache with TTL"""
    try:
        ttl = ttl or settings.redis_cache_ttl
        redis_client.setex(key, ttl, json.dumps(value))
    except Exception:
        pass

def cache_delete(key: str):
    """Delete key from cache"""
    try:
        redis_client.delete(key)
    except Exception:
        pass

def cache_delete_pattern(pattern: str):
    """Delete all keys matching pattern"""
    try:
        for key in redis_client.scan_iter(match=pattern):
            redis_client.delete(key)
    except Exception:
        pass

# Cache invalidation helpers
def invalidate_user_cache(user_id: int):
    """Invalidate all cache for a user"""
    cache_delete_pattern(f"user:{user_id}:*")
    cache_delete_pattern(f"addresses:{user_id}")
    cache_delete_pattern(f"tier:{user_id}")

def invalidate_address_cache(address: str):
    """Invalidate cache for an email address"""
    cache_delete(f"policy:{address}")
    cache_delete(f"address:{address}")

def invalidate_tier_cache(user_id: int):
    """Invalidate tier-related cache"""
    cache_delete(f"tier:{user_id}")
    cache_delete_pattern(f"user:{user_id}:addresses")
