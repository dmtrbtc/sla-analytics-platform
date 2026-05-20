"""Enterprise Integrations V2 — API tokens, webhook management, Slack/Teams/Jira/OTRS adapters."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import sync_session_factory

logger = logging.getLogger(__name__)


# === API TOKENS ===

def generate_api_token(user_id: UUID, name: str, permissions: list[str] | None = None) -> dict:
    """Generate a scoped API token for a user."""
    db = sync_session_factory()
    try:
        token_value = f"sla_{secrets.token_hex(32)}"
        token_hash = hashlib.sha256(token_value.encode()).hexdigest()
        token_id = uuid.uuid4()

        db.execute(
            text("""
                INSERT INTO api_tokens (id, user_id, name, token_hash, permissions, created_at, expires_at)
                VALUES (:id, :uid, :name, :hash, :perms, NOW(), NOW() + INTERVAL '365 days')
            """),
            {
                "id": token_id,
                "uid": user_id,
                "name": name,
                "hash": token_hash,
                "perms": json.dumps(permissions or ["*"]),
            },
        )
        db.commit()
        return {"token_id": str(token_id), "token": token_value, "name": name}
    finally:
        db.close()


def validate_api_token(token: str) -> Optional[dict]:
    """Validate an API token and return associated user info."""
    db = sync_session_factory()
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        row = db.execute(
            text("""
                SELECT t.id, t.user_id, t.name, t.permissions, t.expires_at, u.email, u.role
                FROM api_tokens t
                JOIN users u ON u.id = t.user_id
                WHERE t.token_hash = :hash AND t.is_active = True AND (t.expires_at IS NULL OR t.expires_at > NOW())
            """),
            {"hash": token_hash},
        ).first()
        if not row:
            return None
        return {
            "token_id": str(row.id),
            "user_id": str(row.user_id),
            "name": row.name,
            "permissions": row.permissions or ["*"],
            "email": row.email,
            "role": row.role,
        }
    finally:
        db.close()


def revoke_api_token(token_id: UUID) -> bool:
    """Revoke an API token."""
    db = sync_session_factory()
    try:
        db.execute(text("UPDATE api_tokens SET is_active = False WHERE id = :id"), {"id": token_id})
        db.commit()
        return True
    finally:
        db.close()


# === WEBHOOK MANAGEMENT ===

def register_webhook(organization_id: UUID, name: str, url: str, events: list[str], secret: str | None = None) -> dict:
    """Register a webhook endpoint."""
    db = sync_session_factory()
    try:
        wh_id = uuid.uuid4()
        wh_secret = secret or secrets.token_hex(32)
        db.execute(
            text("""
                INSERT INTO webhooks (id, organization_id, name, url, events, secret, is_active, created_at)
                VALUES (:id, :oid, :name, :url, :events, :secret, True, NOW())
            """),
            {"id": wh_id, "oid": organization_id, "name": name, "url": url, "events": json.dumps(events), "secret": wh_secret},
        )
        db.commit()
        return {"webhook_id": str(wh_id), "secret": wh_secret}
    finally:
        db.close()


def dispatch_webhook(organization_id: UUID, event_type: str, payload: dict) -> list[dict]:
    """Dispatch an event to all matching webhooks."""
    db = sync_session_factory()
    results = []
    try:
        hooks = db.execute(
            text("SELECT id, url, secret, events FROM webhooks WHERE organization_id = :oid AND is_active = True"),
            {"oid": organization_id},
        ).all()

        for hook in hooks:
            hook_events = hook.events or []
            if "*" not in hook_events and event_type not in hook_events:
                continue

            try:
                body = json.dumps({"event": event_type, "payload": payload, "timestamp": datetime.now(timezone.utc).isoformat()})
                signature = hmac.new(hook.secret.encode(), body.encode(), hashlib.sha256).hexdigest()
                with httpx.Client(timeout=10) as client:
                    resp = client.post(
                        hook.url,
                        content=body,
                        headers={"Content-Type": "application/json", "X-SLA-Signature": signature},
                    )
                results.append({"webhook_id": str(hook.id), "status": resp.status_code, "success": resp.is_success})
            except Exception as exc:
                results.append({"webhook_id": str(hook.id), "error": str(exc), "success": False})
    finally:
        db.close()
    return results


# === SLACK INTEGRATION ===

def send_slack_notification(webhook_url: str, message: str, blocks: list[dict] | None = None) -> dict:
    """Send a notification to Slack via webhook."""
    try:
        payload: dict[str, Any] = {"text": message}
        if blocks:
            payload["blocks"] = blocks
        with httpx.Client(timeout=10) as client:
            resp = client.post(webhook_url, json=payload)
        return {"status": resp.status_code, "success": resp.is_success}
    except Exception as exc:
        return {"error": str(exc), "success": False}


# === TEAMS INTEGRATION ===

def send_teams_notification(webhook_url: str, title: str, message: str) -> dict:
    """Send a notification to Microsoft Teams via webhook."""
    try:
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "summary": title,
            "title": title,
            "text": message,
        }
        with httpx.Client(timeout=10) as client:
            resp = client.post(webhook_url, json=payload)
        return {"status": resp.status_code, "success": resp.is_success}
    except Exception as exc:
        return {"error": str(exc), "success": False}


# === JIRA INTEGRATION ===

def create_jira_issue(base_url: str, token: str, project: str, summary: str, description: str, issue_type: str = "Bug") -> dict:
    """Create a Jira issue via REST API."""
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                f"{base_url}/rest/api/2/issue",
                json={
                    "fields": {
                        "project": {"key": project},
                        "summary": summary,
                        "description": description,
                        "issuetype": {"name": issue_type},
                    }
                },
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
        return {"status": resp.status_code, "issue_key": resp.json().get("key") if resp.is_success else None, "success": resp.is_success}
    except Exception as exc:
        return {"error": str(exc), "success": False}


# === OTRS ADAPTER ===

def query_otrs_ticket(otrs_url: str, token: str, ticket_id: int) -> Optional[dict]:
    """Query an OTRS ticket via REST API (GenericTicketConnector)."""
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(
                f"{otrs_url}/nph-genericinterface.pl/Webservice/TicketConnector/Ticket/{ticket_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
        if resp.is_success:
            return resp.json()
        return None
    except Exception as exc:
        logger.warning("OTRS query failed for ticket %s: %s", ticket_id, exc)
        return None
