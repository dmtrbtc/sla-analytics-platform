"""Celery monitoring: correlation IDs, task timing, audit trail."""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone

from celery import Task
from sqlalchemy import text

from app.core.database import sync_session_factory

logger = logging.getLogger(__name__)


def generate_correlation_id() -> str:
    return f"task-{uuid.uuid4().hex[:12]}"


class MonitoredTask(Task):
    """Base task class with correlation ID, timing, and audit logging."""

    abstract = True
    _correlation_id: str = ""

    def on_before_task(self, task_id, args, kwargs):
        self._correlation_id = kwargs.pop("_correlation_id", generate_correlation_id())
        kwargs["_correlation_id"] = self._correlation_id
        self._start_time = time.monotonic()
        logger.info(
            "Task started",
            extra={
                "correlation_id": self._correlation_id,
                "task_name": self.name,
                "task_id": task_id,
            },
        )

    def on_success(self, retval, task_id, args, kwargs):
        # on_before_task is not auto-invoked by Celery's standard lifecycle
        # — _start_time may not be set, so fall back gracefully.
        start = getattr(self, "_start_time", None)
        elapsed = (time.monotonic() - start) if start is not None else 0.0
        logger.info(
            "Task completed",
            extra={
                "correlation_id": getattr(self, "_correlation_id", ""),
                "task_name": self.name,
                "task_id": task_id,
                "duration_ms": round(elapsed * 1000, 1),
            },
        )
        self._record_task_execution(task_id, "completed", elapsed)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        # Same guard: never let the failure handler itself raise — that
        # masks the real exception and makes tasks look like they retry
        # forever without ever surfacing the underlying error.
        start = getattr(self, "_start_time", None)
        elapsed = (time.monotonic() - start) if start is not None else 0.0
        logger.error(
            "Task failed",
            extra={
                "correlation_id": getattr(self, "_correlation_id", ""),
                "task_name": self.name,
                "task_id": task_id,
                "duration_ms": round(elapsed * 1000, 1),
                "error": str(exc),
            },
        )
        try:
            self._record_task_execution(task_id, "failed", elapsed, str(exc))
        except Exception:
            logger.exception("task_audit record failed")

    def _record_task_execution(self, task_id: str, status: str, duration_ms: float, error: str = ""):
        try:
            db = sync_session_factory()
            try:
                db.execute(
                    text("""
                        INSERT INTO task_audit (task_id, task_name, correlation_id, status, duration_ms, error, started_at)
                        VALUES (:task_id, :task_name, :correlation_id, :status, :duration_ms, :error, :started_at)
                    """),
                    {
                        "task_id": task_id,
                        "task_name": self.name,
                        "correlation_id": self._correlation_id,
                        "status": status,
                        "duration_ms": duration_ms,
                        "error": error,
                        "started_at": datetime.now(timezone.utc),
                    },
                )
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.warning("Failed to record task audit for %s: %s", task_id, e)


def get_task_audit(limit: int = 100, offset: int = 0) -> list[dict]:
    db = sync_session_factory()
    try:
        rows = db.execute(
            text("SELECT * FROM task_audit ORDER BY started_at DESC LIMIT :limit OFFSET :offset"),
            {"limit": limit, "offset": offset},
        ).mappings().all()
        return [dict(r) for r in rows]
    finally:
        db.close()
