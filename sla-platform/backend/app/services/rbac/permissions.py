"""Advanced RBAC — permission groups, fine-grained access, queue-level visibility."""
from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import sync_session_factory
from app.core.dependencies import get_current_user
from app.domain.enums import UserRole
from app.domain.models import User

logger = logging.getLogger(__name__)

# Permission matrix: action -> allowed roles
PERMISSION_MATRIX: dict[str, list[str]] = {
    # Dashboard access
    "dashboard:view": ["admin", "analyst", "team_lead", "viewer"],
    "dashboard:executive": ["admin", "analyst"],
    "dashboard:wallboard": ["admin", "analyst", "team_lead", "viewer"],

    # Import management
    "import:create": ["admin", "analyst"],
    "import:view": ["admin", "analyst", "team_lead", "viewer"],
    "import:delete": ["admin"],
    "import:reprocess": ["admin", "analyst"],

    # SLA management
    "sla:config": ["admin"],
    "sla:view": ["admin", "analyst", "team_lead", "viewer"],
    "sla:monitor": ["admin", "analyst", "team_lead"],

    # Ticket access
    "ticket:view": ["admin", "analyst", "team_lead", "viewer"],
    "ticket:export": ["admin", "analyst"],

    # Analytics
    "analytics:view": ["admin", "analyst", "team_lead"],
    "analytics:export": ["admin", "analyst"],
    "analytics:forecast": ["admin", "analyst"],

    # AI Copilot
    "ai:query": ["admin", "analyst", "team_lead"],
    "ai:executive_summary": ["admin", "analyst"],
    "ai:incident_summary": ["admin", "analyst"],

    # Reports
    "report:create": ["admin", "analyst"],
    "report:view": ["admin", "analyst", "team_lead", "viewer"],
    "report:export": ["admin", "analyst"],

    # Team management
    "team:config": ["admin"],
    "team:view": ["admin", "analyst", "team_lead"],

    # User management
    "user:admin": ["admin"],
    "user:view": ["admin", "analyst"],

    # Organization admin
    "org:admin": ["admin"],
    "org:quotas": ["admin"],

    # System
    "system:diagnostics": ["admin"],
    "system:traces": ["admin"],
    "system:health": ["admin", "analyst", "team_lead", "viewer"],

    # Operations
    "ops:incidents": ["admin", "analyst"],
    "ops:self_healing": ["admin"],
    "ops:auto_mitigate": ["admin"],

    # Security
    "security:audit": ["admin"],
    "security:exports": ["admin"],

    # Billing
    "billing:view": ["admin"],
    "billing:admin": ["admin"],

    # Integrations
    "integration:admin": ["admin"],
    "integration:webhook": ["admin"],
}

# Access groups (named permission sets)
ACCESS_GROUPS: dict[str, list[str]] = {
    "admin_full": list(PERMISSION_MATRIX.keys()),
    "analyst_standard": [
        "dashboard:view", "dashboard:executive", "dashboard:wallboard",
        "import:create", "import:view", "import:reprocess",
        "sla:view", "sla:monitor",
        "ticket:view", "ticket:export",
        "analytics:view", "analytics:export", "analytics:forecast",
        "ai:query", "ai:executive_summary", "ai:incident_summary",
        "report:create", "report:view", "report:export",
        "team:view",
        "user:view",
        "system:health",
        "ops:incidents",
    ],
    "team_lead_limited": [
        "dashboard:view", "dashboard:wallboard",
        "import:view",
        "sla:view", "sla:monitor",
        "ticket:view",
        "analytics:view",
        "ai:query",
        "report:view",
        "team:view",
        "system:health",
    ],
    "viewer_readonly": [
        "dashboard:view", "dashboard:wallboard",
        "import:view",
        "sla:view",
        "ticket:view",
        "report:view",
        "system:health",
    ],
}


def has_permission(user: User, permission: str) -> bool:
    """Check if a user has a specific permission based on their role."""
    allowed_roles = PERMISSION_MATRIX.get(permission, [])
    return user.role in allowed_roles


def require_permission(permission: str):
    """Dependency factory for fine-grained access control."""
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if not has_permission(current_user, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Доступ запрещён: требуется право '{permission}'",
            )
        return current_user
    return _check


def get_visible_queues(user: User) -> list[str]:
    """Return queue names visible to this user (admin=all, team_lead=team queues)."""
    if user.role == UserRole.ADMIN:
        return ["*"]
    if user.role == UserRole.TEAM_LEAD:
        db = sync_session_factory()
        try:
            rows = db.execute(
                text("""
                    SELECT DISTINCT t.queue_prefix
                    FROM teams t
                    JOIN user_teams ut ON ut.team_id = t.id
                    WHERE ut.user_id = :uid
                """),
                {"uid": user.id},
            ).all()
            return [r[0] for r in rows]
        finally:
            db.close()
    return ["*"]


def get_user_permissions(user: User) -> list[str]:
    """Return all permissions for a user."""
    return [perm for perm in PERMISSION_MATRIX if has_permission(user, perm)]


def get_role_permissions(role: str) -> list[str]:
    """Return all permissions for a role."""
    key_map = {"admin": "admin_full", "analyst": "analyst_standard", "team_lead": "team_lead_limited", "viewer": "viewer_readonly"}
    key = key_map.get(role, "viewer_readonly")
    return ACCESS_GROUPS.get(key, [])
