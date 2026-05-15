"""Redis cache layer with key prefixes, TTL management, and invalidation."""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

CACHE_PREFIX = "sla:"
DEFAULT_TTL = 300  # 5 minutes
ANALYTICS_TTL = 600  # 10 minutes
DASHBOARD_TTL = 120  # 2 minutes


def _get_client():
    import redis as sync_redis

    return sync_redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        socket_connect_timeout=2,
        decode_responses=True,
    )


def cache_key(*parts: str) -> str:
    return f"{CACHE_PREFIX}{':'.join(parts)}"


def get(key: str) -> Optional[Any]:
    try:
        r = _get_client()
        val = r.get(key)
        r.close()
        return json.loads(val) if val else None
    except Exception as exc:
        logger.debug("Cache get failed: %s", exc)
        return None


def set(key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
    try:
        r = _get_client()
        r.setex(key, ttl, json.dumps(value))
        r.close()
        return True
    except Exception as exc:
        logger.debug("Cache set failed: %s", exc)
        return False


def delete(*keys: str) -> int:
    try:
        r = _get_client()
        count = r.delete(*keys)
        r.close()
        return count
    except Exception as exc:
        logger.debug("Cache delete failed: %s", exc)
        return 0


def delete_pattern(pattern: str) -> int:
    try:
        r = _get_client()
        cursor = 0
        deleted = 0
        while True:
            cursor, keys = r.scan(cursor=cursor, match=f"{CACHE_PREFIX}{pattern}", count=100)
            if keys:
                deleted += r.delete(*keys)
            if cursor == 0:
                break
        r.close()
        return deleted
    except Exception as exc:
        logger.debug("Cache delete pattern failed: %s", exc)
        return 0


def cached(ttl: int = DEFAULT_TTL, key_prefix: str = ""):
    """Decorator: cache function result in Redis."""
    def decorator(fn: Callable):
        async def wrapper(*args, **kwargs):
            key = cache_key(key_prefix or fn.__name__, *(str(a) for a in args), *(f"{k}={v}" for k, v in sorted(kwargs.items())))
            cached_val = get(key)
            if cached_val is not None:
                return cached_val
            result = await fn(*args, **kwargs)
            set(key, result, ttl)
            return result
        return wrapper
    return decorator


def invalidate_dashboard_cache() -> int:
    return delete_pattern("get_overview*")


def invalidate_analytics_cache() -> int:
    return delete_pattern("analytics*")
