"""Redis Event Bus — async publish/subscribe for real-time operational events.

Channels:
  - sla.events: SLA breach, risk change, escalation triggered
  - ops.alerts: queue overload, worker down, import completed
  - analytics.events: computation complete, materialized view refresh
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Channel names
CHANNEL_SLA = "sla.events"
CHANNEL_OPS = "ops.alerts"
CHANNEL_ANALYTICS = "analytics.events"

# Event types
EVENT_SLA_BREACH = "sla_breach"
EVENT_TICKET_CREATED = "ticket_created"
EVENT_TICKET_UPDATED = "ticket_updated"
EVENT_QUEUE_OVERLOADED = "queue_overloaded"
EVENT_RISK_CHANGED = "risk_changed"
EVENT_ESCALATION_TRIGGERED = "escalation_triggered"
EVENT_WORKER_DOWN = "worker_down"
EVENT_IMPORT_COMPLETED = "import_completed"
EVENT_ANOMALY_DETECTED = "anomaly_detected"
EVENT_INCIDENT_CREATED = "incident_created"
EVENT_INCIDENT_RESOLVED = "incident_resolved"


def _get_async_client():
    import redis.asyncio as aioredis

    return aioredis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        socket_connect_timeout=2,
        decode_responses=True,
    )


def _get_sync_client():
    import redis as sync_redis

    return sync_redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        socket_connect_timeout=2,
        decode_responses=True,
    )


async def publish_event(channel: str, event_type: str, data: dict[str, Any]) -> bool:
    """Publish an event to a Redis pub/sub channel (async)."""
    try:
        r = await _get_async_client()
        payload = json.dumps({"type": event_type, "data": data})
        await r.publish(channel, payload)
        await r.aclose()
        return True
    except Exception as exc:
        logger.warning("Failed to publish event %s to %s: %s", event_type, channel, exc)
        return False


def publish_event_sync(channel: str, event_type: str, data: dict[str, Any]) -> bool:
    """Publish an event to a Redis pub/sub channel (sync — for Celery tasks)."""
    try:
        r = _get_sync_client()
        payload = json.dumps({"type": event_type, "data": data})
        r.publish(channel, payload)
        r.close()
        return True
    except Exception as exc:
        logger.warning("Failed to publish event %s to %s: %s", event_type, channel, exc)
        return False


def publish_ws_event(event: dict[str, Any]) -> None:
    """Publish an event to the WebSocket Redis channel (Celery-friendly)."""
    from app.core.websocket_manager import REDIS_WS_CHANNEL, publish_ws_event as _pub
    _pub(event)


async def subscribe_events(channel: str, handler: Callable[[dict[str, Any]], None]) -> None:
    """Subscribe to a Redis pub/sub channel and call handler for each message."""
    try:
        r = await _get_async_client()
        pubsub = r.pubsub()
        await pubsub.subscribe(channel)
        logger.info("Subscribed to channel: %s", channel)
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                event = json.loads(message["data"])
                await handler(event)
            except Exception as exc:
                logger.warning("Event handler error on %s: %s", channel, exc)
    except Exception as exc:
        logger.error("Subscription error on %s: %s", channel, exc)
