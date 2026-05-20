"""Tenant isolation middleware — row-level filtering, quota enforcement, organization context."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.database import get_db, sync_session_factory
from app.core.dependencies import get_current_user
from app.domain.models import User

logger = logging.getLogger(__name__)

ORG_HEADER = "X-Organization-ID"


async def get_org_context(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Extract and validate organization context from request."""
    org_id_str = request.headers.get(ORG_HEADER)
    if not org_id_str:
        return {"organization_id": None, "is_multi_tenant": False}

    try:
        org_id = UUID(org_id_str)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid organization ID format")

    row = await db.execute(
        text("SELECT id, name, slug, is_active FROM organizations WHERE id = :oid"),
        {"oid": org_id},
    )
    org = row.first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if not org.is_active:
        raise HTTPException(status_code=403, detail="Organization is deactivated")

    return {"organization_id": org_id, "is_multi_tenant": True, "org_name": org.name, "org_slug": org.slug}


def check_quota(organization_id: UUID, resource: str) -> bool:
    """Check if an organization has quota remaining for a resource."""
    db = sync_session_factory()
    try:
        quota = db.execute(
            text("SELECT * FROM organization_quotas WHERE organization_id = :oid"),
            {"oid": organization_id},
        ).first()
        if not quota:
            return True

        since = datetime.now(timezone.utc) - timedelta(days=1)

        if resource == "import":
            max_val = quota.max_imports_per_day
            used = db.execute(
                text("SELECT COUNT(*) FROM import_sessions WHERE imported_by IN (SELECT id FROM users WHERE organization_id = :oid) AND created_at >= :since"),
                {"oid": organization_id, "since": since},
            ).scalar() or 0
            if used >= max_val:
                return False

        elif resource == "export":
            max_val = quota.max_exports_per_day
            used = db.execute(
                text("SELECT COUNT(*) FROM task_audit WHERE task_name LIKE '%export%' AND started_at >= :since"),
                {"since": since},
            ).scalar() or 0
            if used >= max_val:
                return False

        return True
    finally:
        db.close()


def require_quota(organization_id: UUID, resource: str):
    """Decorator to enforce quota limits."""
    if not check_quota(organization_id, resource):
        raise HTTPException(status_code=429, detail=f"Daily quota exceeded for {resource}")


async def add_org_id_to_entity(db: AsyncSession, entity: str, entity_id: Any, organization_id: UUID) -> None:
    """Associate an entity with an organization (for multi-tenant setup)."""
    await db.execute(
        text(f"UPDATE {entity} SET organization_id = :oid WHERE id = :eid"),
        {"oid": organization_id, "eid": entity_id},
    )
    await db.commit()


async def get_branding(organization_id: UUID) -> dict:
    """Return organization branding configuration."""
    db = sync_session_factory()
    try:
        row = db.execute(
            text("SELECT * FROM organization_branding WHERE organization_id = :oid"),
            {"oid": organization_id},
        ).first()
        if row:
            return {
                "logo_url": row.logo_url,
                "primary_color": row.primary_color,
                "secondary_color": row.secondary_color,
                "timezone": row.timezone,
                "locale": row.locale,
            }
        return {}
    finally:
        db.close()
