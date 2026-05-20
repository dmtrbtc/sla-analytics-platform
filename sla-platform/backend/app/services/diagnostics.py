"""Observability V2 — system diagnostics, health checks, and metrics."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.cache import cache_key, get, set, delete
from app.core.config import settings
from app.core.database import sync_session_factory

logger = logging.getLogger(__name__)


def _check_db_pool(db: Session) -> dict:
    """Return database connection pool metrics."""
    stats = {}
    try:
        row = db.execute(
            text("""
                SELECT
                    numbackends,
                    xact_commit,
                    xact_rollback,
                    blks_read,
                    blks_hit,
                    tup_returned,
                    tup_fetched,
                    tup_inserted,
                    tup_updated,
                    tup_deleted,
                    conflicts,
                    deadlocks
                FROM pg_stat_database
                WHERE datname = current_database()
            """)
        ).first()
        if row:
            stats = {
                "backends": row[0],
                "commits": row[1],
                "rollbacks": row[2],
                "cache_hit_ratio": round(row[4] / max(row[3] + row[4], 1) * 100, 2),
                "tuples_fetched": row[6],
                "tuples_inserted": row[7],
                "conflicts": row[10],
                "deadlocks": row[11],
            }
    except Exception as exc:
        stats = {"error": str(exc)}

    # Active queries
    try:
        active = db.execute(
            text("""
                SELECT COUNT(*) FROM pg_stat_activity
                WHERE state = 'active'
                  AND pid != pg_backend_pid()
                  AND query NOT LIKE '%pg_stat_activity%'
            """)
        ).scalar() or 0
        stats["active_queries"] = active
    except Exception:
        pass

    # Connection pool
    try:
        pool = db.execute(
            text("""
                SELECT
                    count(*) FILTER (WHERE state = 'idle') AS idle,
                    count(*) FILTER (WHERE state = 'active') AS active,
                    count(*) FILTER (WHERE state = 'idle in transaction') AS idle_in_trans
                FROM pg_stat_activity
                WHERE backend_type = 'client backend'
            """)
        ).first()
        if pool:
            stats["pool_idle"] = pool[0]
            stats["pool_active"] = pool[1]
            stats["pool_idle_in_transaction"] = pool[2]
    except Exception:
        pass

    return stats


def _check_redis() -> dict:
    """Return Redis connection health and memory stats."""
    try:
        import redis as sync_redis

        r = sync_redis.Redis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB,
            socket_connect_timeout=2, decode_responses=True,
        )
        info = r.info()
        memory = info.get("used_memory_human", "N/A")
        total_keys = info.get("db0", {}).get("keys", 0) if "db0" in info else r.dbsize()

        # Cache hit/miss from info
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 1)
        hit_ratio = round(hits / max(hits + misses, 1) * 100, 2)

        # Check cache prefix keys
        sla_cache_keys = r.keys("sla:*")
        cache_memory = sum(len(k) + len(r.get(k) or "") for k in sla_cache_keys)

        r.close()
        return {
            "connected": True,
            "memory_used": memory,
            "total_keys": total_keys,
            "sla_cache_keys": len(sla_cache_keys),
            "sla_cache_memory_bytes": cache_memory,
            "hit_ratio_pct": hit_ratio,
            "uptime_days": round(info.get("uptime_in_seconds", 0) / 86400, 2),
        }
    except Exception as exc:
        return {"connected": False, "error": str(exc)}


def _check_celery_workers() -> dict:
    """Return Celery worker pool status."""
    try:
        from celery import Celery

        app = Celery(broker=settings.CELERY_BROKER_URL)
        insp = app.control.inspect()
        stats = insp.stats() or {}
        registered = insp.registered() or {}

        workers = {}
        total_active = 0
        total_scheduled = 0
        for worker_name, worker_stats in stats.items():
            workers[worker_name] = {
                "concurrency": worker_stats.get("pool", {}).get("max-concurrency", "N/A"),
                "processed": worker_stats.get("total", {}).get("total", 0),
                "active": len(worker_stats.get("active", [])),
                "scheduled": len(worker_stats.get("scheduled", [])),
                "uptime": worker_stats.get("uptime", 0),
            }
            total_active += workers[worker_name]["active"]
            total_scheduled += workers[worker_name]["scheduled"]

        return {
            "connected": True,
            "worker_count": len(workers),
            "workers": workers,
            "registered_tasks": list(registered.keys()) if registered else [],
            "total_active_tasks": total_active,
            "total_scheduled_tasks": total_scheduled,
        }
    except Exception as exc:
        return {"connected": False, "error": str(exc)}


def _check_queue_lag() -> dict:
    """Check Redis queue backlog sizes for each Celery queue."""
    try:
        import redis as sync_redis

        r = sync_redis.Redis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0,
            socket_connect_timeout=2, decode_responses=True,
        )
        queues = ["celery", "imports", "reports", "maintenance", "analytics", "dead_letter"]
        lag = {}
        for q in queues:
            length = r.llen(q)
            lag[q] = length
        r.close()
        return lag
    except Exception as exc:
        return {"error": str(exc)}


def _check_scheduler_health() -> dict:
    """Check if Beat scheduler is running by looking for heartbeat."""
    try:
        import redis as sync_redis

        r = sync_redis.Redis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0,
            socket_connect_timeout=2, decode_responses=True,
        )
        beat_heartbeat = r.get("celery-beat-heartbeat")
        r.close()
        return {
            "beat_running": beat_heartbeat is not None,
            "last_heartbeat": str(beat_heartbeat) if beat_heartbeat else None,
        }
    except Exception as exc:
        return {"error": str(exc)}


def _check_task_audit() -> dict:
    """Return recent task audit stats."""
    try:
        db = sync_session_factory()
        row = db.execute(
            text("""
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE status = 'completed') AS completed,
                    COUNT(*) FILTER (WHERE status = 'failed') AS failed,
                    COUNT(*) FILTER (WHERE started_at >= NOW() - INTERVAL '1 hour') AS last_hour,
                    ROUND(AVG(duration_ms))::int AS avg_duration_ms
                FROM task_audit
                WHERE started_at >= NOW() - INTERVAL '24 hours'
            """)
        ).first()
        db.close()
        if row:
            return {
                "total_24h": row[0],
                "completed_24h": row[1],
                "failed_24h": row[2],
                "last_hour_tasks": row[3],
                "avg_duration_ms": row[4],
                "success_rate_pct": round(row[1] / max(row[0], 1) * 100, 2),
            }
        return {}
    except Exception as exc:
        return {"error": str(exc)}


def _check_materialized_views() -> dict:
    """Return materialized view refresh status."""
    from app.services.analytics.materialized_view_service import check_view_staleness

    try:
        db = sync_session_factory()
        status = check_view_staleness(db)
        db.close()
        stale = [s["view_name"] for s in status if s.get("is_stale")]
        missing = [s["view_name"] for s in status if not s.get("exists")]
        return {
            "total": len(status),
            "stale_count": len(stale),
            "missing_count": len(missing),
            "stale_views": stale,
            "missing_views": missing,
            "views": status,
        }
    except Exception as exc:
        return {"error": str(exc)}


def get_full_diagnostics() -> dict:
    """Aggregate all system diagnostics into a single response."""
    start = time.monotonic()
    db = sync_session_factory()

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.VERSION,
        "db_pool": _check_db_pool(db),
        "redis": _check_redis(),
        "celery_workers": _check_celery_workers(),
        "queue_lag": _check_queue_lag(),
        "scheduler": _check_scheduler_health(),
        "task_audit": _check_task_audit(),
        "materialized_views": _check_materialized_views(),
    }

    db.close()
    result["elapsed_ms"] = round((time.monotonic() - start) * 1000, 1)
    return result


def get_live_health() -> dict:
    """Lightweight health check — quick ping to each service."""
    start = time.monotonic()
    db = sync_session_factory()

    health = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.VERSION,
    }

    # DB ping
    try:
        db.execute(text("SELECT 1"))
        health["database"] = "ok"
    except Exception:
        health["database"] = "error"
        health["status"] = "degraded"

    db.close()

    # Redis ping
    try:
        import redis as sync_redis

        r = sync_redis.Redis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB,
            socket_connect_timeout=2,
        )
        r.ping()
        r.close()
        health["redis"] = "ok"
    except Exception:
        health["redis"] = "error"
        health["status"] = "degraded"

    health["elapsed_ms"] = round((time.monotonic() - start) * 1000, 1)
    return health
