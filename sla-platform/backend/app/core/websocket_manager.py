"""WebSocket connection manager for real-time updates.

Provides:
- Authenticated WebSocket connections via token query param
- Per-client event subscriptions
- Heartbeat/ping every 30s
- Redis pub/sub bridge for cross-process event broadcasting
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Callable, Optional

from fastapi import WebSocket, WebSocketDisconnect

from app.core.config import settings

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = 30
MAX_CLIENTS = 500
REDIS_WS_CHANNEL = "ws:events"


class ConnectionManager:
    """Manages WebSocket connections with auth and event routing."""

    def __init__(self) -> None:
        self._connections: dict[str, WebSocket] = {}
        self._user_map: dict[str, str] = {}  # client_id -> user_id
        self._heartbeat_tasks: dict[str, asyncio.Task] = {}
        self._redis_listener_task: Optional[asyncio.Task] = None

    async def connect(self, ws: WebSocket, client_id: str, user_id: str) -> None:
        if len(self._connections) >= MAX_CLIENTS:
            logger.warning("Max WebSocket clients reached (%d)", MAX_CLIENTS)
            await ws.close(code=1013, reason="Too many connections")
            return
        await ws.accept()
        self._connections[client_id] = ws
        self._user_map[client_id] = user_id
        self._heartbeat_tasks[client_id] = asyncio.create_task(
            self._heartbeat_loop(client_id)
        )
        if self._redis_listener_task is None:
            self._redis_listener_task = asyncio.create_task(
                self._redis_pubsub_listener()
            )
        logger.info("WebSocket connected: client=%s user=%s", client_id, user_id)

    async def disconnect(self, client_id: str) -> None:
        self._connections.pop(client_id, None)
        self._user_map.pop(client_id, None)
        task = self._heartbeat_tasks.pop(client_id, None)
        if task:
            task.cancel()
        if not self._connections and self._redis_listener_task:
            self._redis_listener_task.cancel()
            self._redis_listener_task = None
        logger.info("WebSocket disconnected: client=%s", client_id)

    async def _heartbeat_loop(self, client_id: str) -> None:
        """Send ping frames every HEARTBEAT_INTERVAL seconds."""
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            ws = self._connections.get(client_id)
            if not ws:
                break
            try:
                await ws.send_json({"type": "ping", "ts": time.time()})
            except Exception:
                break

    async def _redis_pubsub_listener(self) -> None:
        """Listen for events from Celery workers via Redis pub/sub."""
        try:
            import redis.asyncio as aioredis

            r = aioredis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                socket_connect_timeout=2,
                socket_keepalive=True,
            )
            pubsub = r.pubsub()
            await pubsub.subscribe(REDIS_WS_CHANNEL)
            logger.info("Redis pub/sub listener started on %s", REDIS_WS_CHANNEL)
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    event = json.loads(message["data"])
                    await self.broadcast(event)
                except Exception as exc:
                    logger.warning("Failed to broadcast WS event: %s", exc)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("Redis pub/sub listener error: %s", exc)

    async def send_personal(self, client_id: str, event: dict[str, Any]) -> bool:
        ws = self._connections.get(client_id)
        if not ws:
            return False
        try:
            await ws.send_json(event)
            return True
        except Exception:
            await self.disconnect(client_id)
            return False

    async def broadcast(self, event: dict[str, Any]) -> int:
        sent = 0
        for client_id in list(self._connections.keys()):
            ok = await self.send_personal(client_id, event)
            if ok:
                sent += 1
        return sent

    async def broadcast_to_users(self, user_ids: set[str], event: dict[str, Any]) -> int:
        sent = 0
        for client_id, uid in self._user_map.items():
            if uid in user_ids:
                ok = await self.send_personal(client_id, event)
                if ok:
                    sent += 1
        return sent

    @property
    def active_connections(self) -> int:
        return len(self._connections)


manager = ConnectionManager()


async def handle_ws_events(ws: WebSocket, token_payload: dict) -> None:
    """Main WebSocket event loop for a connected client."""
    from uuid import uuid4

    client_id = str(uuid4())
    user_id = token_payload.get("sub", "unknown")
    await manager.connect(ws, client_id, user_id)

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await manager.send_personal(client_id, {
                    "type": "error", "message": "Invalid JSON",
                })
                continue

            msg_type = data.get("type", "")

            if msg_type == "pong":
                continue

            if msg_type == "subscribe":
                channels = data.get("channels", [])
                await manager.send_personal(client_id, {
                    "type": "subscribed",
                    "channels": channels,
                })
                continue

            if msg_type == "unsubscribe":
                await manager.send_personal(client_id, {
                    "type": "unsubscribed",
                })
                continue

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WebSocket error client=%s: %s", client_id, exc)
    finally:
        await manager.disconnect(client_id)


def publish_ws_event(event: dict[str, Any]) -> None:
    """Publish an event to the Redis pub/sub channel (called from Celery tasks)."""
    try:
        import redis as sync_redis
        r = sync_redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            socket_connect_timeout=2,
        )
        r.publish(REDIS_WS_CHANNEL, json.dumps(event))
        r.close()
    except Exception as exc:
        logger.warning("Failed to publish WS event: %s", exc)

