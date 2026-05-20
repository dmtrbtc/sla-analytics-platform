"""Distributed SLA compute orchestrator — partitions tickets, tracks progress, manages queues."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_cache, invalidate_analytics_cache
from app.core.celery_app import celery_app
from app.core.database import sync_session_factory
from app.domain.models import SLADefinition, TicketSnapshot
from app.services.sla.batch_metrics_engine import compute_metrics_batch

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
MAX_PARTITIONS = 50

_ORCHESTRATOR_PREFIX = "sla:orchestrator"


def _get_redis():
    import redis as sync_redis
    from app.core.config import settings

    return sync_redis.Redis(
        host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB,
        socket_connect_timeout=2, decode_responses=True,
    )


def _progress_key(import_id: str) -> str:
    return f"{_ORCHESTRATOR_PREFIX}:{import_id}:progress"


def _partitions_key(import_id: str) -> str:
    return f"{_ORCHESTRATOR_PREFIX}:{import_id}:partitions"


def _status_key(import_id: str) -> str:
    return f"{_ORCHESTRATOR_PREFIX}:{import_id}:status"


def partition_tickets(tickets: list) -> list[list[int]]:
    total = len(tickets)
    n_parts = min(max(1, total // CHUNK_SIZE), MAX_PARTITIONS)
    if n_parts <= 1:
        return [[t.ticket_id for t in tickets]]
    parts = []
    for i in range(n_parts):
        start = i * total // n_parts
        end = (i + 1) * total // n_parts
        parts.append([t.ticket_id for t in tickets[start:end]])
    return parts


def init_orchestration(import_id: str, sla_defs: list, total_tickets: int) -> dict:
    r = _get_redis()
    r.set(_status_key(import_id), "initialized")
    r.set(_progress_key(import_id), json.dumps({
        "total": total_tickets, "completed": 0, "failed": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }))
    r.expire(_progress_key(import_id), 86400)
    r.expire(_status_key(import_id), 86400)

    priority = 5
    for sd in sla_defs:
        p = getattr(sd, 'priority', None)
        if p and str(p).lower() in ("critical", "high"):
            priority = 3
            break
    r.close()
    return {"import_id": import_id, "total_tickets": total_tickets, "priority": priority}


def launch_distributed_compute(import_id: str) -> dict:
    """Launch distributed SLA computation across partitions."""
    db = sync_session_factory()
    try:
        tickets = db.query(TicketSnapshot).filter(
            TicketSnapshot.last_import_id == import_id
        ).all()
        sla_defs = db.query(SLADefinition).filter(
            SLADefinition.is_active == True
        ).all()

        init_orchestration(import_id, sla_defs, len(tickets))

        # Delete existing metrics once
        db.execute(text("DELETE FROM sla_metrics WHERE import_id = :import_id"), {"import_id": import_id})
        db.commit()

        partitions = partition_tickets(tickets)

        tasks = []
        for i, part in enumerate(partitions):
            tasks.append(compute_partition_task.s(import_id, part, i))

        from celery import group
        job = group(tasks)
        result = job.apply_async(priority=3)

        r = _get_redis()
        r.set(_partitions_key(import_id), json.dumps({
            "total": len(partitions),
            "launched_at": datetime.now(timezone.utc).isoformat(),
        }))
        r.expire(_partitions_key(import_id), 86400)
        r.close()

        return {
            "import_id": import_id,
            "partitions": len(partitions),
            "tickets": len(tickets),
        }
    except Exception as exc:
        logger.exception("Failed to launch distributed compute for %s", import_id)
        return {"import_id": import_id, "error": str(exc)}
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, soft_time_limit=1800, time_limit=2100, queue="sla_compute")
def compute_partition_task(self, import_id: str, ticket_ids: list[int], partition_index: int) -> dict:
    """Compute SLA metrics for a single partition."""
    from app.services.sla.metrics_engine import MetricsEngine
    from app.services.sla.batch_metrics_engine import compute_metrics_batch, _bulk_insert_metrics
    from app.services.sla.rule_engine import match_sla

    db = sync_session_factory()
    try:
        tickets = db.query(TicketSnapshot).filter(
            TicketSnapshot.ticket_id.in_(ticket_ids)
        ).all()
        sla_defs = db.query(SLADefinition).filter(
            SLADefinition.is_active == True
        ).all()

        metrics_written = 0
        errors = []

        for sla_def in sla_defs:
            matched = [t for t in tickets if match_sla(t, sla_defs) and match_sla(t, sla_defs).id == sla_def.id]
            if not matched:
                continue
            try:
                metrics = compute_metrics_batch(db, matched, sla_def, import_id)
                written = _bulk_insert_metrics(db, metrics)
                metrics_written += written
            except Exception as exc:
                logger.exception("Partition %d sla_def %s failed", partition_index, sla_def.name)
                errors.append({"sla_def": sla_def.name, "error": str(exc)})

        _update_progress(import_id, len(ticket_ids), len(errors))
        logger.info("Partition %d done: %d metrics, %d errors", partition_index, metrics_written, len(errors))
        return {"partition": partition_index, "metrics_written": metrics_written, "errors": errors}
    except Exception as exc:
        _update_progress(import_id, 0, len(ticket_ids))
        try:
            self.retry(countdown=30 * (2 ** self.request.retries))
        except Exception:
            pass
        return {"partition": partition_index, "error": str(exc)}
    finally:
        db.close()


def _update_progress(import_id: str, completed: int, failed: int) -> dict:
    r = _get_redis()
    try:
        raw = r.get(_progress_key(import_id))
        prog = json.loads(raw) if raw else {"total": 0, "completed": 0, "failed": 0}
        prog["completed"] += completed
        prog["failed"] += failed
        prog["updated_at"] = datetime.now(timezone.utc).isoformat()
        r.set(_progress_key(import_id), json.dumps(prog))
        r.expire(_progress_key(import_id), 86400)
        return prog
    finally:
        r.close()


def get_orchestration_status(import_id: str) -> dict:
    r = _get_redis()
    try:
        return {
            "import_id": import_id,
            "status": r.get(_status_key(import_id)) or "unknown",
            "progress": json.loads(r.get(_progress_key(import_id))) if r.get(_progress_key(import_id)) else None,
            "partitions": json.loads(r.get(_partitions_key(import_id))) if r.get(_partitions_key(import_id)) else None,
        }
    finally:
        r.close()
