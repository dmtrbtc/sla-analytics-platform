"""WebSocket connection manager for real-time updates.

Provides:
- Authenticated WebSocket connections via token query param
- Per-client event subscriptions (channels)
- Heartbeat/ping every 30s
- Redis pub/sub bridge for cross-process event broadcasting
- Channel-based routing (/ws/dashboard, /ws/ops, /ws/tickets, /ws/alerts)
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Optional

from fastapi import WebSocket, WebSocketDisconnect

from app.core.config import settings

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = 30
MAX_CLIENTS = 1000
REDIS_WS_CHANNEL = "ws:events"


class ConnectionManager:
    """Manages WebSocket connections with auth and event routing."""

    def __init__(self) -> None:
        self._connections: dict[str, WebSocket] = {}
        self._user_map: dict[str, str] = {}
        self._channels: dict[str, set[str]] = {}  # channel -> set of client_ids
        self._client_channels: dict[str, set[str]] = {}  # client_id -> set of channels
        self._heartbeat_tasks: dict[str, asyncio.Task] = {}
        self._redis_listener_task: Optional[asyncio.Task] = None

    async def connect(self, ws: WebSocket, client_id: str, user_id: str, channel: str = "default") -> None:
        if len(self._connections) >= MAX_CLIENTS:
            logger.warning("Max WebSocket clients reached (%d)", MAX_CLIENTS)
            await ws.close(code=1013, reason="Too many connections")
            return
        await ws.accept()
        self._connections[client_id] = ws
        self._user_map[client_id] = user_id
        self._client_channels.setdefault(client_id, set()).add(channel)
        self._channels.setdefault(channel, set()).add(client_id)
        self._heartbeat_tasks[client_id] = asyncio.create_task(self._heartbeat_loop(client_id))
        if self._redis_listener_task is None:
            self._redis_listener_task = asyncio.create_task(self._redis_pubsub_listener())
        logger.info("WebSocket connected: client=%s user=%s channel=%s", client_id, user_id, channel)
        await ws.send_json({"type": "connected", "client_id": client_id, "channel": channel})

    async def disconnect(self, client_id: str) -> None:
        self._connections.pop(client_id, None)
        self._user_map.pop(client_id, None)
        for ch in self._client_channels.pop(client_id, set()):
            self._channels.get(ch, set()).discard(client_id)
        task = self._heartbeat_tasks.pop(client_id, None)
        if task:
            task.cancel()
        if not self._connections and self._redis_listener_task:
            self._redis_listener_task.cancel()
            self._redis_listener_task = None
        logger.info("WebSocket disconnected: client=%s", client_id)

    async def subscribe(self, client_id: str, channel: str) -> None:
        self._client_channels.setdefault(client_id, set()).add(channel)
        self._channels.setdefault(channel, set()).add(client_id)
        logger.debug("Client %s subscribed to %s", client_id, channel)

    async def unsubscribe(self, client_id: str, channel: str) -> None:
        self._client_channels.get(client_id, set()).discard(channel)
        self._channels.get(channel, set()).discard(client_id)

    async def _heartbeat_loop(self, client_id: str) -> None:
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
        try:
            import redis.asyncio as aioredis
            r = aioredis.Redis(
                host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB,
                socket_connect_timeout=2, socket_keepalive=True,
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
        target_channel = event.get("channel", "")
        for client_id in list(self._connections.keys()):
            if target_channel and target_channel not in self._client_channels.get(client_id, set()):
                continue
            ok = await self.send_personal(client_id, event)
            if ok:
                sent += 1
        return sent

    async def broadcast_to_channel(self, channel: str, event: dict[str, Any]) -> int:
        sent = 0
        for client_id in list(self._channels.get(channel, set())):
            ok = await self.send_personal(client_id, event)
            if ok:
                sent += 1
        return sent

    @property
    def active_connections(self) -> int:
        return len(self._connections)

    def get_stats(self) -> dict[str, Any]:
        return {
            "connections": len(self._connections),
            "channels": {ch: len(cls) for ch, cls in self._channels.items()},
            "heartbeat_tasks": len(self._heartbeat_tasks),
        }


manager = ConnectionManager()


async def handle_ws_events(ws: WebSocket, token_payload: dict, channel: str = "default") -> None:
    """Main WebSocket event loop for a connected client."""
    from uuid import uuid4
    client_id = str(uuid4())
    user_id = token_payload.get("sub", "unknown")
    await manager.connect(ws, client_id, user_id, channel)

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await manager.send_personal(client_id, {"type": "error", "message": "Invalid JSON"})
                continue

            msg_type = data.get("type", "")

            if msg_type == "pong":
                continue

            if msg_type == "subscribe":
                channels = data.get("channels", [])
                for ch in channels:
                    await manager.subscribe(client_id, ch)
                await manager.send_personal(client_id, {"type": "subscribed", "channels": channels})
                continue

            if msg_type == "unsubscribe":
                channels = data.get("channels", [])
                for ch in channels:
                    await manager.unsubscribe(client_id, ch)
                await manager.send_personal(client_id, {"type": "unsubscribed"})
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
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB,
            socket_connect_timeout=2,
        )
        r.publish(REDIS_WS_CHANNEL, json.dumps(event))
        r.close()
    except Exception as exc:
        logger.warning("Failed to publish WS event: %s", exc)
