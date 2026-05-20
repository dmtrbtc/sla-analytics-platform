"""Notification Celery tasks — email, webhook, telegram alerts."""
import json
import logging
from datetime import datetime, timezone

import requests

from app.core.celery_app import celery_app, exponential_backoff
from app.core.config import settings
from app.core.database import sync_session_factory

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, soft_time_limit=60, time_limit=90)
def send_email_notification(self, to: str, subject: str, body: str) -> dict:
    """Send email notification (SMTP)."""
    try:
        logger.info("Email notification to %s: %s", to, subject)
        # Placeholder — integrate with SMTP in production
        return {"to": to, "subject": subject, "sent": True}
    except Exception:
        try:
            self.retry(countdown=exponential_backoff(self))
        except Exception:
            raise


@celery_app.task(bind=True, max_retries=3, soft_time_limit=30, time_limit=45)
def send_webhook_notification(self, url: str, payload: dict) -> dict:
    """Send webhook notification."""
    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        return {"url": url, "status": resp.status_code}
    except Exception:
        try:
            self.retry(countdown=exponential_backoff(self))
        except Exception:
            raise


@celery_app.task(bind=True, max_retries=3, soft_time_limit=30, time_limit=45)
def send_telegram_notification(self, chat_id: str, message: str) -> dict:
    """Send Telegram notification."""
    try:
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        if not token:
            logger.warning("TELEGRAM_BOT_TOKEN not configured")
            return {"sent": False, "error": "not configured"}
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=15)
        resp.raise_for_status()
        return {"chat_id": chat_id, "sent": True}
    except Exception:
        try:
            self.retry(countdown=exponential_backoff(self))
        except Exception:
            raise


@celery_app.task(bind=True, max_retries=2, soft_time_limit=60, time_limit=90)
def broadcast_alert(self, channel: str, event_type: str, data: dict) -> dict:
    """Broadcast alert through Redis pub/sub."""
    from app.core.events import publish_event_sync

    try:
        publish_event_sync(channel, event_type, data)
        return {"channel": channel, "event_type": event_type, "broadcast": True}
    except Exception:
        try:
            self.retry(countdown=exponential_backoff(self))
        except Exception:
            raise
