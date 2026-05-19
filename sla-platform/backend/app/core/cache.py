"""Redis cache layer with key prefixes, TTL management, and invalidation."""
from __future__ import annotations

import functools
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


def _make_cache_key(fn: Callable, args: tuple, kwargs: dict, skip_args: int = 0) -> str:
    parts = [fn.__name__]
    for a in args[skip_args:]:
        if hasattr(a, "__name__"):
            parts.append(a.__name__)
        else:
            parts.append(str(a))
    for k in sorted(kwargs):
        v = kwargs[k]
        if hasattr(v, "__name__"):
            parts.append(f"{k}={v.__name__}")
        else:
            parts.append(f"{k}={v}")
    return cache_key(*parts)


def cached(ttl: int = DEFAULT_TTL, key_prefix: str = "", skip_args: int = 0):
    """Decorator: cache async function result in Redis.
    skip_args: number of leading positional args to exclude from cache key (e.g. db session).
    """
    def decorator(fn: Callable):
        async def wrapper(*args, **kwargs):
            key = _make_cache_key(fn, args, kwargs, skip_args)
            if key_prefix:
                key = cache_key(key_prefix, key)
            cached_val = get(key)
            if cached_val is not None:
                return cached_val
            result = await fn(*args, **kwargs)
            set(key, result, ttl)
            return result
        return wrapper
    return decorator


def cached_sync(ttl: int = DEFAULT_TTL, key_prefix: str = "", skip_args: int = 0):
    """Decorator: cache sync function result in Redis.
    skip_args: number of leading positional args to exclude from cache key (e.g. db session).
    """
    def decorator(fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = _make_cache_key(fn, args, kwargs, skip_args)
            if key_prefix:
                key = cache_key(key_prefix, key)
            cached_val = get(key)
            if cached_val is not None:
                return cached_val
            result = fn(*args, **kwargs)
            set(key, result, ttl)
            return result
        return wrapper
    return decorator


def invalidate_dashboard_cache() -> int:
    return delete_pattern("get_overview*")


def invalidate_analytics_cache() -> int:
    return delete_pattern("analytics*")
