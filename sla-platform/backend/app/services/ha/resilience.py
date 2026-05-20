"""HA + Resilience — Redis failover, Postgres replica awareness, queue failover, graceful degradation."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import sync_session_factory

logger = logging.getLogger(__name__)


def check_redis_health() -> dict:
    """Check Redis health and detect failover state."""
    try:
        import redis as sync_redis

        r = sync_redis.Redis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB,
            socket_connect_timeout=2, decode_responses=True,
        )
        info = r.info()
        role = info.get("role", "unknown")
        connected_slaves = info.get("connected_slaves", 0)
        r.close()
        return {
            "role": role,
            "connected_slaves": connected_slaves,
            "healthy": role == "master" or connected_slaves > 0,
            "failover_detected": role == "slave" and connected_slaves == 0,
        }
    except Exception as exc:
        return {"healthy": False, "error": str(exc), "failover_needed": True}


def check_postgres_replicas() -> dict:
    """Check Postgres replica lag and health."""
    db = sync_session_factory()
    try:
        primary = db.execute(text("SELECT pg_is_in_recovery()")).scalar()
        if primary is False:
            # We are on primary — check replica lag
            replicas = db.execute(
                text("""
                    SELECT client_addr, state, sent_lsn, write_lag, replay_lag
                    FROM pg_stat_replication
                """)
            ).all()
            return {
                "is_primary": True,
                "replica_count": len(replicas),
                "replicas": [
                    {"addr": str(r.client_addr), "state": r.state} for r in replicas
                ],
                "healthy": True,
            }
        else:
            return {"is_primary": False, "is_replica": True, "healthy": True}
    except Exception as exc:
        return {"healthy": False, "error": str(exc)}
    finally:
        db.close()


def check_queue_failover() -> dict:
    """Check if Celery queues are backed up (potential failover needed)."""
    try:
        import redis as sync_redis

        r = sync_redis.Redis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0,
            socket_connect_timeout=2, decode_responses=True,
        )
        queues = ["celery", "imports", "sla_compute", "analytics", "exports", "notifications"]
        lag = {}
        for q in queues:
            length = r.llen(q)
            lag[q] = length
        r.close()

        critical_lag = {q: l for q, l in lag.items() if l > 500}
        return {
            "queue_lag": lag,
            "critical_queues": critical_lag,
            "failover_needed": len(critical_lag) > 0,
        }
    except Exception as exc:
        return {"error": str(exc), "failover_needed": True}


def graceful_degradation_check() -> dict:
    """Determine if system should enter graceful degradation mode."""
    redis_status = check_redis_health()
    pg_status = check_postgres_replicas()
    queue_status = check_queue_failover()

    degradation_level = "none"
    reasons = []

    if not redis_status.get("healthy"):
        degradation_level = "partial"
        reasons.append("Redis unhealthy — caching degraded")

    if not pg_status.get("healthy"):
        degradation_level = "critical"
        reasons.append("Postgres unhealthy — read-only mode recommended")

    if queue_status.get("failover_needed"):
        if degradation_level == "none":
            degradation_level = "partial"
        reasons.append(f"Queue backlog critical: {queue_status.get('critical_queues', {})}")

    return {
        "degradation_level": degradation_level,
        "reasons": reasons,
        "redis": redis_status,
        "postgres": pg_status,
        "queues": queue_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "recommended_action": "switch_to_readonly" if degradation_level == "critical" else "monitor" if degradation_level == "partial" else "none",
    }


def get_worker_autoscaling_metrics() -> dict:
    """Return metrics for HPA decision-making."""
    db = sync_session_factory()
    try:
        # Active import count
        active_imports = db.execute(
            text("SELECT COUNT(*) FROM import_sessions WHERE status IN ('validating','parsing','normalizing','rebuilding','computing_sla')")
        ).scalar() or 0

        # Pending SLA compute (from task_audit)
        pending_tasks = db.execute(
            text("SELECT COUNT(*) FROM task_audit WHERE status = 'running' AND started_at >= NOW() - INTERVAL '1 hour'")
        ).scalar() or 0

        return {
            "active_imports": active_imports,
            "pending_tasks_1h": pending_tasks,
            "suggested_sla_workers": min(20, max(2, active_imports // 2 + 2)),
            "suggested_import_workers": min(10, max(1, active_imports // 3 + 1)),
        }
    finally:
        db.close()
