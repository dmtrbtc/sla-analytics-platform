"""Self-healing operations — auto mitigation, stuck detection, recovery engine, diagnostics snapshots."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_cache, invalidate_analytics_cache
from app.core.celery_app import celery_app, exponential_backoff
from app.core.database import sync_session_factory
from app.core.events import publish_event_sync, CHANNEL_OPS, CHANNEL_ANALYTICS
from app.domain.enums import ImportStatus
from app.domain.models import ImportSession

logger = logging.getLogger(__name__)


# === STUCK DETECTION ===

def detect_stuck_imports(hours: int = 2) -> list[dict]:
    """Detect imports stuck in intermediate states for > N hours."""
    db = sync_session_factory()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        stuck = db.query(ImportSession).filter(
            ImportSession.status.in_([
                ImportStatus.VALIDATING.value, ImportStatus.PARSING.value,
                ImportStatus.NORMALIZING.value, ImportStatus.REBUILDING.value,
                ImportStatus.COMPUTING_SLA.value,
            ]),
            ImportSession.updated_at < cutoff,
        ).all()

        results = []
        for imp in stuck:
            results.append({
                "import_id": str(imp.id),
                "status": imp.status,
                "stuck_for_hours": round((datetime.now(timezone.utc) - imp.updated_at).total_seconds() / 3600, 1),
                "created_at": str(imp.created_at),
            })
        return results
    finally:
        db.close()


def detect_stalled_views() -> list[dict]:
    """Check materialized views for staleness."""
    from app.services.analytics.materialized_view_service import check_view_staleness

    db = sync_session_factory()
    try:
        return check_view_staleness(db)
    finally:
        db.close()


def detect_queue_lag_anomaly(max_acceptable: int = 100) -> dict:
    """Detect abnormal queue backlog sizes."""
    try:
        import redis as sync_redis
        from app.core.config import settings

        r = sync_redis.Redis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0,
            socket_connect_timeout=2, decode_responses=True,
        )
        queues = ["celery", "imports", "reports", "maintenance", "analytics", "sla_compute", "exports", "notifications"]
        lag = {}
        for q in queues:
            length = r.llen(q)
            lag[q] = length
        r.close()

        anomalous = {q: l for q, l in lag.items() if l > max_acceptable}
        return {
            "queue_lag": lag,
            "anomalous_queues": anomalous,
            "has_anomaly": len(anomalous) > 0,
        }
    except Exception as exc:
        return {"error": str(exc)}


# === AUTO MITIGATION ===

def auto_mitigate() -> list[dict]:
    """Run auto-mitigation actions for detected issues."""
    actions = []

    # 1. Auto-retry stuck imports
    stuck = detect_stuck_imports(hours=2)
    for s in stuck:
        try:
            _auto_retry_import(s["import_id"])
            actions.append({
                "type": "auto_retry_import",
                "target": s["import_id"],
                "reason": f"Stuck for {s['stuck_for_hours']}h in {s['status']}",
                "status": "triggered",
            })
        except Exception as exc:
            actions.append({
                "type": "auto_retry_import",
                "target": s["import_id"],
                "reason": str(exc),
                "status": "failed",
            })

    # 2. Auto-refresh stale views
    stale_views = detect_stalled_views()
    stale = [v for v in stale_views if v.get("is_stale")]
    for sv in stale:
        try:
            _auto_refresh_view(sv["view_name"])
            actions.append({
                "type": "auto_refresh_view",
                "target": sv["view_name"],
                "reason": "Stale materialized view",
                "status": "triggered",
            })
        except Exception as exc:
            actions.append({
                "type": "auto_refresh_view",
                "target": sv["view_name"],
                "reason": str(exc),
                "status": "failed",
            })

    # 3. Auto-recompute on queue lag anomaly
    lag_status = detect_queue_lag_anomaly(max_acceptable=200)
    if lag_status.get("has_anomaly"):
        publish_event_sync(CHANNEL_OPS, "queue_lag_anomaly", lag_status)
        actions.append({
            "type": "queue_lag_alert",
            "target": "celery_monitor",
            "reason": f"Abnormal queue lag: {lag_status['anomalous_queues']}",
            "status": "alerted",
        })

    # 4. Auto-refresh analytics cache
    try:
        invalidate_dashboard_cache()
        invalidate_analytics_cache()
        actions.append({
            "type": "auto_refresh_cache",
            "target": "analytics_cache",
            "reason": "Scheduled cache refresh",
            "status": "triggered",
        })
    except Exception as exc:
        actions.append({
            "type": "auto_refresh_cache",
            "target": "analytics_cache",
            "reason": str(exc),
            "status": "failed",
        })

    return actions


def _auto_retry_import(import_id: str) -> None:
    """Re-queue a stuck import."""
    db = sync_session_factory()
    try:
        imp = db.query(ImportSession).filter_by(id=import_id).first()
        if imp:
            imp.status = ImportStatus.VALIDATING.value
            db.commit()
            from app.tasks.import_tasks import run_import_pipeline
            run_import_pipeline.delay(str(imp.id))
            logger.info("Auto-retried import %s", import_id)
    finally:
        db.close()


def _auto_refresh_view(view_name: str) -> None:
    """Refresh a specific materialized view."""
    from app.services.analytics.materialized_view_service import refresh_view

    db = sync_session_factory()
    try:
        refresh_view(db, view_name, concurrently=True)
        logger.info("Auto-refreshed view %s", view_name)
    finally:
        db.close()


# === RECOVERY ENGINE ===

def recovery_snapshot() -> dict:
    """Take a diagnostics snapshot for recovery purposes."""
    from app.services.diagnostics import get_full_diagnostics
    return get_full_diagnostics()


def run_recovery_policies() -> list[dict]:
    """Evaluate and run recovery policies."""
    policies = []

    # Policy 1: Restart stuck workers
    try:
        from celery import Celery
        from app.core.config import settings

        app = Celery(broker=settings.CELERY_BROKER_URL)
        insp = app.control.inspect()
        stats = insp.stats() or {}
        for worker, wstats in stats.items():
            active = len(wstats.get("active", []))
            scheduled = len(wstats.get("scheduled", []))
            if active == 0 and scheduled > 5:
                policies.append({
                    "worker": worker,
                    "policy": "soft_restart_suggested",
                    "reason": f"{scheduled} scheduled tasks but 0 active",
                    "action": "check worker health",
                })
    except Exception as exc:
        policies.append({"policy": "worker_health_check", "error": str(exc)})

    # Policy 2: Diagnose DB connection pool
    try:
        db = sync_session_factory()
        pool = db.execute(
            text("""
                SELECT COUNT(*) AS active,
                       COUNT(*) FILTER (WHERE state = 'idle') AS idle,
                       COUNT(*) FILTER (WHERE state = 'active') AS active_conn
                FROM pg_stat_activity WHERE backend_type = 'client backend'
            """)
        ).first()
        db.close()
        if pool and pool.active_conn > 50:
            policies.append({
                "policy": "db_connection_saturation",
                "reason": f"{pool.active_conn} active connections (threshold 50)",
                "action": "increase pool_size or reduce concurrent workers",
            })
    except Exception:
        pass

    return policies


# === CELERY TASKS ===

@celery_app.task(bind=True, max_retries=2, soft_time_limit=120, time_limit=180)
def auto_heal_check(self) -> dict:
    """Periodic self-healing check — detect issues and auto-mitigate."""
    db = sync_session_factory()
    try:
        stuck = detect_stuck_imports(hours=2)
        stale_views = detect_stalled_views()
        lag = detect_queue_lag_anomaly()

        mitigation = auto_mitigate()

        return {
            "stuck_imports": len(stuck),
            "stale_views": sum(1 for v in stale_views if v.get("is_stale")),
            "queue_lag_anomaly": lag.get("has_anomaly"),
            "mitigation_actions": len(mitigation),
            "actions": mitigation,
        }
    finally:
        db.close()
