"""Observability setup: structured logging, Prometheus metrics, health checks, request timing."""

import os
import time
from typing import Callable

import structlog
from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

# ---------------------------------------------------------------------------
# Custom Prometheus metrics
# ---------------------------------------------------------------------------

celery_task_duration = Histogram(
    "celery_task_duration_seconds",
    "Duration of Celery tasks by name and status",
    ["task_name", "status"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0, float("inf")),
)

celery_tasks_total = Counter(
    "celery_tasks_total",
    "Total number of Celery tasks by name and status",
    ["task_name", "status"],
)

db_query_duration = Histogram(
    "db_query_duration_seconds",
    "Duration of database queries",
    ["query_type"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0),
)

sla_metrics_processed = Counter(
    "sla_metrics_processed_total",
    "Total number of SLA metrics processed",
    ["import_id", "status"],
)

import_pipeline_duration = Histogram(
    "import_pipeline_duration_seconds",
    "Duration of import pipeline stages",
    ["stage", "import_id"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600),
)

imports_total = Counter(
    "imports_total",
    "Total number of imports by status",
    ["status"],
)

active_imports = Gauge(
    "active_imports",
    "Number of currently active imports",
)

queue_backlog = Gauge(
    "queue_backlog",
    "Current backlog count by queue",
    ["queue_name"],
)

error_counter = Counter(
    "app_errors_total",
    "Total number of application errors by type",
    ["error_type", "endpoint"],
)


def increment_error_counter(error_type: str, endpoint: str) -> None:
    error_counter.labels(error_type=error_type, endpoint=endpoint).inc()


def observe_db_query(duration: float, query_type: str) -> None:
    db_query_duration.labels(query_type=query_type).observe(duration)


# ---------------------------------------------------------------------------
# Structured logging (structlog)
# ---------------------------------------------------------------------------

def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# ---------------------------------------------------------------------------
# Request timing middleware
# ---------------------------------------------------------------------------

class RequestTimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        elapsed = time.monotonic() - start
        response.headers["X-Request-Time-Ms"] = str(round(elapsed * 1000, 1))
        return response


# ---------------------------------------------------------------------------
# Health check endpoint
# ---------------------------------------------------------------------------

async def health_check(request=None):
    """Comprehensive health endpoint exposing dependency status."""
    from app.core.database import sync_session_factory

    services = {"app": "healthy"}

    # DB check
    try:
        db = sync_session_factory()
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db.close()
        services["database"] = "healthy"
    except Exception:
        services["database"] = "unhealthy"

    # Redis check
    import socket
    try:
        s = socket.create_connection((settings.REDIS_HOST, settings.REDIS_PORT), timeout=2)
        s.close()
        services["redis"] = "healthy"
    except Exception:
        services["redis"] = "unhealthy"

    overall = "healthy" if all(v == "healthy" for v in services.values()) else "degraded"
    return {"status": overall, "version": settings.VERSION, "services": services}


# ---------------------------------------------------------------------------
# Apply all observability to app
# ---------------------------------------------------------------------------

def configure_observability(app: FastAPI) -> None:
    configure_logging()

    # Prometheus metrics
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    # Request timing
    app.add_middleware(RequestTimingMiddleware)

    # Health check is defined in main.py — nothing to override here
