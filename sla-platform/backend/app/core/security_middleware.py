"""Security middleware: rate limiting, request size, CORS hardening, exception handling."""

import logging
import time
from typing import Callable

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rate limiter (in-memory token bucket)
# ---------------------------------------------------------------------------

class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self._buckets: dict[str, list[float]] = {}

    def check(self, key: str) -> bool:
        now = time.time()
        window = 60.0
        if key not in self._buckets:
            self._buckets[key] = []
        self._buckets[key] = [t for t in self._buckets[key] if now - t < window]
        if len(self._buckets[key]) >= self.rpm:
            return False
        self._buckets[key].append(now)
        return True


_rate_limiter = RateLimiter()


EXCLUDED_PATHS = frozenset({"/health", "/api/docs", "/api/openapi.json"})


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{request.url.path}"

        if not _rate_limiter.check(key):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down."},
                headers={"Retry-After": "60"},
            )

        return await call_next(request)


# ---------------------------------------------------------------------------
# Centralized exception handler
# ---------------------------------------------------------------------------

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception serving %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for err in exc.errors():
        errors.append({
            "field": " -> ".join(str(loc) for loc in err.get("loc", [])),
            "message": err.get("msg", ""),
            "type": err.get("type", ""),
        })
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation failed", "errors": errors},
    )


# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "same-origin"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response


# ---------------------------------------------------------------------------
# Apply all security middleware to app
# ---------------------------------------------------------------------------

def configure_security(app: FastAPI) -> None:
    """Register all security middleware on the FastAPI app."""

    # Stricter CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "X-Requested-With",
        ],
        max_age=600,
    )

    # Rate limiting
    app.add_middleware(RateLimitMiddleware)

    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Exception handlers (order matters — specific before generic)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)
