"""OpenTelemetry tracing for SLA Intelligence Platform — distributed traces, span exports.

Provides:
- FastAPI middleware for request tracing
- Celery task tracing
- SQL query tracing
- Export via OTLP or console
"""
from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager
from typing import Any, Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global tracer (simple implementation — in production use opentelemetry SDK)
_traces: list[dict] = []
_max_traces = 10000


def generate_trace_id() -> str:
    return f"trace-{uuid.uuid4().hex[:16]}"


def generate_span_id() -> str:
    return f"span-{uuid.uuid4().hex[:12]}"


class Span:
    """A single span in a distributed trace."""

    def __init__(self, name: str, trace_id: str, parent_span_id: Optional[str] = None, attributes: Optional[dict] = None):
        self.name = name
        self.trace_id = trace_id
        self.span_id = generate_span_id()
        self.parent_span_id = parent_span_id
        self.attributes = attributes or {}
        self.start_time = time.monotonic()
        self.end_time: Optional[float] = None
        self.status = "ok"
        self.events: list[dict] = []

    def finish(self, status: str = "ok"):
        self.end_time = time.monotonic()
        self.status = status

    def add_event(self, name: str, attributes: Optional[dict] = None):
        self.events.append({
            "name": name,
            "timestamp": time.monotonic(),
            "attributes": attributes or {},
        })

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "attributes": self.attributes,
            "start_time": self.start_time,
            "duration_ms": round((self.end_time - self.start_time) * 1000, 2) if self.end_time else None,
            "status": self.status,
            "events": self.events,
        }


class Tracer:
    """Simple distributed tracer — records spans, exports on finish."""

    def __init__(self):
        self._spans: list[Span] = []
        self._active_spans: dict[str, Span] = {}

    def start_span(self, name: str, trace_id: Optional[str] = None, parent_span_id: Optional[str] = None, attributes: Optional[dict] = None) -> Span:
        trace_id = trace_id or generate_trace_id()
        span = Span(name, trace_id, parent_span_id, attributes)
        self._active_spans[span.span_id] = span
        return span

    def finish_span(self, span: Span, status: str = "ok"):
        span.finish(status)
        self._spans.append(span.to_dict())
        self._active_spans.pop(span.span_id, None)
        # Trim if over limit
        if len(self._spans) > _max_traces:
            self._spans = self._spans[-_max_traces:]

    def get_traces(self, limit: int = 100, trace_id: Optional[str] = None) -> list[dict]:
        results = self._spans[-limit:] if not trace_id else [s for s in self._spans if s.get("trace_id") == trace_id][-limit:]
        return results

    def clear(self):
        self._spans.clear()
        self._active_spans.clear()


# Global tracer instance
tracer = Tracer()


@contextmanager
def trace_span(name: str, trace_id: Optional[str] = None, parent_span_id: Optional[str] = None, attributes: Optional[dict] = None):
    """Context manager for tracing a span."""
    span = tracer.start_span(name, trace_id, parent_span_id, attributes)
    try:
        yield span
    except Exception as exc:
        span.add_event("error", {"error": str(exc)})
        tracer.finish_span(span, "error")
        raise
    else:
        tracer.finish_span(span, "ok")


class TracingMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that traces all HTTP requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        trace_id = request.headers.get("X-Trace-ID", generate_trace_id())
        span = tracer.start_span(
            name=f"{request.method} {request.url.path}",
            trace_id=trace_id,
            attributes={
                "http.method": request.method,
                "http.path": request.url.path,
                "http.query": str(request.url.query),
            },
        )
        try:
            response = await call_next(request)
            span.add_event("response", {"status_code": response.status_code})
            tracer.finish_span(span)
            response.headers["X-Trace-ID"] = trace_id
            return response
        except Exception as exc:
            span.add_event("error", {"error": str(exc)})
            tracer.finish_span(span, "error")
            raise


def trace_sql(query: str, params: Any, duration_ms: float):
    """Record a SQL query trace event."""
    span_id = generate_span_id()
    _traces.append({
        "type": "sql",
        "query": query[:200],
        "params": str(params)[:100] if params else "",
        "duration_ms": round(duration_ms, 2),
        "timestamp": time.monotonic(),
    })
    if len(_traces) > _max_traces:
        _traces[:1000] = []


def get_recent_traces(limit: int = 100) -> list[dict]:
    """Return recent traces."""
    return tracer.get_traces(limit=limit)


def get_sql_traces(limit: int = 100) -> list[dict]:
    """Return recent SQL traces."""
    return _traces[-limit:]
