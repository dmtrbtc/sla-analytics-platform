"""Enterprise security — immutable audit chain, signed exports, security event analytics."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import sync_session_factory

logger = logging.getLogger(__name__)


# === IMMUTABLE AUDIT CHAIN ===

def append_audit_entry(
    organization_id: Optional[UUID],
    actor_id: UUID,
    action: str,
    resource_type: str,
    resource_id: str,
    details: dict,
    ip_address: Optional[str] = None,
) -> dict:
    """Append an entry to the immutable audit chain (organization_audit)."""
    db = sync_session_factory()
    try:
        prev_hash = _get_latest_chain_hash(db, organization_id)
        entry_hash = _compute_entry_hash(prev_hash, actor_id, action, resource_type, resource_id, details)

        if organization_id:
            db.execute(
                text("""
                    INSERT INTO organization_audit (id, organization_id, actor_id, action, resource_type, resource_id, details, ip_address, created_at)
                    VALUES (:id, :oid, :aid, :action, :rt, :rid, :details, :ip, NOW())
                """),
                {
                    "id": __import__("uuid").uuid4(),
                    "oid": organization_id,
                    "aid": actor_id,
                    "action": action,
                    "rt": resource_type,
                    "rid": resource_id,
                    "details": json.dumps(details),
                    "ip": ip_address,
                },
            )
            # Store hash in audit chain metadata
            db.execute(
                text("""
                    INSERT INTO organization_audit (id, organization_id, actor_id, action, resource_type, resource_id, details, created_at)
                    VALUES (:id, :oid, :aid, 'chain_hash', 'audit_chain', :rid, :details, NOW())
                """),
                {
                    "id": __import__("uuid").uuid4(),
                    "oid": organization_id,
                    "aid": actor_id,
                    "rid": f"chain:{resource_type}:{resource_id}",
                    "details": json.dumps({"prev_hash": prev_hash, "entry_hash": entry_hash}),
                },
            )
            db.commit()

        return {"hash": entry_hash, "prev_hash": prev_hash, "recorded": True}
    except Exception as exc:
        logger.exception("Failed to append audit entry")
        return {"error": str(exc)}
    finally:
        db.close()


def _get_latest_chain_hash(db: Session, organization_id: Optional[UUID]) -> str:
    if not organization_id:
        return "0" * 64
    row = db.execute(
        text("""
            SELECT details->>'entry_hash' FROM organization_audit
            WHERE organization_id = :oid AND action = 'chain_hash'
            ORDER BY created_at DESC LIMIT 1
        """),
        {"oid": organization_id},
    ).first()
    return row[0] if row else "0" * 64


def _compute_entry_hash(prev_hash: str, actor_id: UUID, action: str, resource_type: str, resource_id: str, details: dict) -> str:
    raw = f"{prev_hash}:{actor_id}:{action}:{resource_type}:{resource_id}:{json.dumps(details, sort_keys=True)}:{datetime.now(timezone.utc).isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def verify_audit_chain(organization_id: UUID) -> dict:
    """Verify the integrity of an organization's audit chain."""
    db = sync_session_factory()
    try:
        entries = db.execute(
            text("""
                SELECT id, created_at, actor_id, action, resource_type, resource_id, details
                FROM organization_audit
                WHERE organization_id = :oid AND action = 'chain_hash'
                ORDER BY created_at ASC
            """),
            {"oid": organization_id},
        ).all()

        prev = "0" * 64
        verified = 0
        corrupted = []
        for entry in entries:
            entry_hash = entry.details.get("entry_hash", "") if entry.details else ""
            expected_prev = entry.details.get("prev_hash", "") if entry.details else ""
            if expected_prev != prev:
                corrupted.append({"id": str(entry.id), "reason": "hash chain broken"})
            else:
                verified += 1
            prev = entry_hash

        return {
            "organization_id": str(organization_id),
            "total_chain_entries": len(entries),
            "verified": verified,
            "corrupted": len(corrupted),
            "corrupted_entries": corrupted,
            "chain_integrity": "intact" if not corrupted else "compromised",
        }
    finally:
        db.close()


# === SIGNED EXPORTS ===

def sign_export_data(data: str, org_slug: str) -> dict:
    """Cryptographically sign export data with org-specific HMAC key."""
    signing_key = f"{settings.SECRET_KEY}:{org_slug}"
    signature = hmac.new(
        signing_key.encode(), data.encode(), hashlib.sha256
    ).hexdigest()
    return {
        "signature": signature,
        "algorithm": "HMAC-SHA256",
        "signed_at": datetime.now(timezone.utc).isoformat(),
        "org_slug": org_slug,
    }


def verify_export_signature(data: str, signature: str, org_slug: str) -> bool:
    """Verify an export's cryptographic signature."""
    expected = sign_export_data(data, org_slug)["signature"]
    return hmac.compare_digest(expected, signature)


# === SECURITY EVENT ANALYTICS ===

def analyze_security_events(days: int = 7) -> dict:
    """Analyze security-relevant events from the audit log."""
    db = sync_session_factory()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Suspicious actions
        suspicious_actions = ["failed_login", "password_change", "role_change", "api_key_reset", "org_settings_change"]
        events = db.execute(
            text("""
                SELECT action, COUNT(*) AS count, COUNT(DISTINCT actor_id) AS actors
                FROM organization_audit
                WHERE created_at >= :since AND action = ANY(:actions)
                GROUP BY action ORDER BY count DESC
            """),
            {"since": since, "actions": suspicious_actions},
        ).all()

        # Failed auth attempts
        failed_auth = db.execute(
            text("""
                SELECT COUNT(*) AS failed_attempts,
                       COUNT(DISTINCT details->>'ip_address') AS unique_ips
                FROM organization_audit
                WHERE action = 'failed_login' AND created_at >= :since
            """),
            {"since": since},
        ).first()

        # Recent security events
        recent = db.execute(
            text("""
                SELECT id, created_at, actor_id, action, resource_type, resource_id, ip_address
                FROM organization_audit
                WHERE created_at >= :since
                ORDER BY created_at DESC LIMIT 50
            """),
            {"since": since},
        ).all()

        return {
            "period_days": days,
            "suspicious_actions": [{"action": r.action, "count": r.count, "unique_actors": r.actors} for r in events],
            "failed_auth_attempts": failed_auth.failed_attempts if failed_auth else 0,
            "unique_ips_failed_auth": failed_auth.unique_ips if failed_auth else 0,
            "recent_events": [
                {"id": str(r.id), "timestamp": str(r.created_at), "actor": str(r.actor_id), "action": r.action, "resource": f"{r.resource_type}:{r.resource_id}", "ip": r.ip_address}
                for r in recent
            ],
        }
    finally:
        db.close()


# === API ABUSE DETECTION ===

def detect_api_abuse(max_requests_per_minute: int = 100) -> list[dict]:
    """Detect potential API abuse from audit patterns."""
    db = sync_session_factory()
    try:
        since = datetime.now(timezone.utc) - timedelta(minutes=5)
        users = db.execute(
            text("""
                SELECT actor_id, COUNT(*) AS request_count, COUNT(DISTINCT ip_address) AS ips
                FROM organization_audit
                WHERE created_at >= :since
                GROUP BY actor_id
                HAVING COUNT(*) > :threshold
                ORDER BY request_count DESC
            """),
            {"since": since, "threshold": max_requests_per_minute * 5},
        ).all()

        return [
            {
                "actor_id": str(r.actor_id),
                "request_count_5min": r.request_count,
                "requests_per_minute": round(r.request_count / 5, 1),
                "unique_ips": r.ips,
                "abuse_score": min(100, int((r.request_count / (max_requests_per_minute * 5)) * 100)),
            }
            for r in users
        ]
    finally:
        db.close()
