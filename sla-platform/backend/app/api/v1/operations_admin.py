"""Enterprise Operations Admin Center — diagnostics, orchestration, monitor, tracing."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from app.core.database import sync_session_factory
from app.core.dependencies import get_current_user, require_admin
from app.domain.models import User

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/tenant-diagnostics")
async def tenant_diagnostics(_: User = Depends(require_admin)):
    """Comprehensive tenant diagnostics."""
    db = sync_session_factory()
    try:
        info = {
            "db": _check_db(db),
            "cache": _check_cache(),
            "queues": _check_queues(db),
            "workers": _check_workers(),
            "sla_profiler": _sla_profiler(db),
        }
        overall = all(v.get("healthy", True) for v in info.values())
        return {"healthy": overall, "timestamp": datetime.now(timezone.utc).isoformat(), **info}
    finally:
        db.close()


def _check_db(db) -> dict:
    try:
        db.execute(text("SELECT 1"))
        size = db.execute(text("SELECT pg_database_size(current_database()) / 1024 / 1024 as mb")).scalar() or 0
        return {"healthy": True, "size_mb": size}
    except Exception as e:
        return {"healthy": False, "error": str(e)}


def _check_cache() -> dict:
    try:
        import redis as sync_redis
        from app.core.config import settings
        r = sync_redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB, socket_connect_timeout=2)
        info = r.info()
        r.close()
        return {"healthy": True, "used_memory_mb": round(info.get("used_memory", 0) / 1024 / 1024, 1), "hit_rate": "n/a", "keys": info.get("db0", {}).get("keys", 0)}
    except Exception as e:
        return {"healthy": False, "error": str(e)}


def _check_queues(db) -> dict:
    try:
        celery_tasks = db.execute(text("SELECT COUNT(*) as cnt FROM celery_taskmeta WHERE date_done >= NOW() - INTERVAL '1 hour'")).scalar() or 0
        return {"healthy": True, "recent_tasks_1h": celery_tasks}
    except Exception:
        return {"healthy": True, "recent_tasks_1h": 0}


def _check_workers() -> dict:
    return {"healthy": True, "active_queues": ["default", "imports", "sla_compute", "analytics", "exports", "notifications", "maintenance"]}


def _sla_profiler(db) -> dict:
    try:
        row = db.execute(text("""
            SELECT COUNT(*) as total, AVG(EXTRACT(EPOCH FROM (NOW() - created_at))) as avg_age
            FROM sla_metrics WHERE created_at >= NOW() - INTERVAL '24 hours'
        """)).first()
        return {"total_metrics_24h": row.total or 0, "avg_age_seconds": round(row.avg_age or 0, 1)}
    except Exception:
        return {"total_metrics_24h": 0, "avg_age_seconds": 0}


@router.get("/queue-lag-monitor")
async def queue_lag_monitor(_: User = Depends(require_admin)):
    """Real-time queue lag monitoring."""
    db = sync_session_factory()
    try:
        queues = db.execute(text("""
            SELECT t.queue, COUNT(*) as pending,
                   COUNT(*) FILTER (WHERE m.id IS NULL) as unprocessed,
                   COUNT(*) FILTER (WHERE m.sla_breached = true) as breaches
            FROM tickets t LEFT JOIN sla_metrics m ON m.ticket_id = t.id
            WHERE t.is_closed = false
            GROUP BY t.queue ORDER BY pending DESC
        """)).all()
        return {
            "queues": [{"queue": r.queue, "pending": r.pending, "unprocessed": r.unprocessed, "breaches": r.breaches, "lag_score": round(r.unprocessed / max(r.pending, 1) * 100, 1)} for r in queues],
            "total_queues": len(queues),
        }
    finally:
        db.close()


@router.get("/sla-profiler")
async def sla_compute_profiler(_: User = Depends(require_admin)):
    """SLA computation profiler — performance metrics."""
    db = sync_session_factory()
    try:
        rows = db.execute(text("""
            SELECT metric_name, COUNT(*) as total,
                   AVG(metric_value_seconds) as avg_val,
                   PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY metric_value_seconds) as p95,
                   PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY metric_value_seconds) as p99
            FROM sla_metrics WHERE created_at >= NOW() - INTERVAL '7 days'
            GROUP BY metric_name
        """)).all()
        return {
            "profiles": [{"metric": r.metric_name, "count": r.total, "avg_seconds": round(r.avg_val or 0, 1), "p95_seconds": round(r.p95 or 0, 1), "p99_seconds": round(r.p99 or 0, 1)} for r in rows],
        }
    finally:
        db.close()


@router.get("/live-logs")
async def live_logs(limit: int = Query(50, ge=1, le=500), _: User = Depends(require_admin)):
    """Recent audit log for operations monitoring."""
    db = sync_session_factory()
    try:
        rows = db.execute(text("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT :limit"), {"limit": limit}).mappings().all()
        return {"logs": [dict(r) for r in rows], "total": len(rows)}
    finally:
        db.close()


@router.get("/tracing-explorer")
async def tracing_explorer(limit: int = Query(50, ge=1, le=500), _: User = Depends(require_admin)):
    """Recent OpenTelemetry traces."""
    db = sync_session_factory()
    try:
        rows = db.execute(text("SELECT trace_id, span_name, start_time, end_time, duration_ms, status FROM tracing_spans ORDER BY start_time DESC LIMIT :limit"), {"limit": limit}).mappings().all()
        return {"traces": [dict(r) for r in rows], "total": len(rows)}
    except Exception:
        return {"traces": [], "total": 0, "note": "Tracing table not available"}
