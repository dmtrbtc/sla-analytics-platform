"""Observability setup: structured logging, Prometheus metrics, health checks, request timing."""

import os
import time
from typing import Callable

import structlog
from fastapi import FastAPI, Request, Response
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


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
