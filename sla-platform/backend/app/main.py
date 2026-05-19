"""SLA Analytics Platform - Main Application Entry"""
from __future__ import annotations

import json
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.observability import configure_observability, health_check
from app.core.security_middleware import configure_security
from app.core.websocket_manager import handle_ws_events

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up SLA Analytics Platform v%s", settings.VERSION)
    from app.seeds import seed_admin_user, seed_sla_definitions
    seed_sla_definitions()
    seed_admin_user()
    yield
    # Clean shutdown
    logger.info("Shutting down SLA Analytics Platform")
    from app.core.database import async_engine, sync_engine
    await async_engine.dispose()
    sync_engine.dispose()
    logger.info("Database connections closed")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

configure_security(app)
configure_observability(app)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return await health_check()


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    token = ws.query_params.get("token", "")
    if not token:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
        return
    try:
        from jose import jwt as jose_jwt
        payload = jose_jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except Exception:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return
    await handle_ws_events(ws, payload, channel="default")


@app.websocket("/ws/dashboard")
async def ws_dashboard(ws: WebSocket):
    token = ws.query_params.get("token", "")
    if not token:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
        return
    try:
        from jose import jwt as jose_jwt
        payload = jose_jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except Exception:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return
    await handle_ws_events(ws, payload, channel="dashboard")


@app.websocket("/ws/ops")
async def ws_ops(ws: WebSocket):
    token = ws.query_params.get("token", "")
    if not token:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
        return
    try:
        from jose import jwt as jose_jwt
        payload = jose_jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except Exception:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return
    await handle_ws_events(ws, payload, channel="ops")


@app.websocket("/ws/tickets")
async def ws_tickets(ws: WebSocket):
    token = ws.query_params.get("token", "")
    if not token:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
        return
    try:
        from jose import jwt as jose_jwt
        payload = jose_jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except Exception:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return
    await handle_ws_events(ws, payload, channel="tickets")


@app.websocket("/ws/alerts")
async def ws_alerts(ws: WebSocket):
    token = ws.query_params.get("token", "")
    if not token:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
        return
    try:
        from jose import jwt as jose_jwt
        payload = jose_jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except Exception:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return
    await handle_ws_events(ws, payload, channel="alerts")
