"""Organization management endpoints — admin-only tenant admin."""
from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.domain.enums import UserRole
from app.domain.models import User
from app.multi_tenant.isolation import get_branding, add_org_id_to_entity

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/organizations")
async def list_organizations(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(text("SELECT * FROM organizations ORDER BY name"))).mappings().all()
    return {"organizations": [dict(r) for r in rows], "total": len(rows)}


@router.post("/organizations")
async def create_organization(
    data: dict[str, Any],
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.multi_tenant.models import Organization, OrganizationQuota, OrganizationBranding

    org_id = __import__("uuid").uuid4()
    await db.execute(
        text("""
            INSERT INTO organizations (id, name, slug, description, is_active, created_at, updated_at)
            VALUES (:id, :name, :slug, :desc, True, NOW(), NOW())
        """),
        {"id": org_id, "name": data["name"], "slug": data.get("slug", data["name"].lower().replace(" ", "-")), "desc": data.get("description", "")},
    )
    # Default quota
    await db.execute(
        text("""
            INSERT INTO organization_quotas (id, organization_id, created_at, updated_at)
            VALUES (:id, :oid, NOW(), NOW())
        """),
        {"id": __import__("uuid").uuid4(), "oid": org_id},
    )
    # Default branding
    await db.execute(
        text("""
            INSERT INTO organization_branding (id, organization_id, timezone, locale, created_at, updated_at)
            VALUES (:id, :oid, 'UTC', 'ru', NOW(), NOW())
        """),
        {"id": __import__("uuid").uuid4(), "oid": org_id},
    )
    await db.commit()

    return {"organization_id": str(org_id), "name": data["name"]}


@router.get("/organizations/{org_id}")
async def get_organization(
    org_id: UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(text("SELECT * FROM organizations WHERE id = :oid"), {"oid": org_id})).first()
    if not row:
        raise HTTPException(status_code=404, detail="Organization not found")
    branding = await get_branding(org_id)
    return {"organization": dict(row._mapping) if hasattr(row, '_mapping') else dict(row), "branding": branding}


@router.put("/organizations/{org_id}")
async def update_organization(
    org_id: UUID,
    data: dict[str, Any],
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    sets = []
    params = {"oid": org_id}
    for field in ("name", "slug", "description", "is_active"):
        if field in data:
            sets.append(f"{field} = :{field}")
            params[field] = data[field]
    if sets:
        sets.append("updated_at = NOW()")
        await db.execute(text(f"UPDATE organizations SET {', '.join(sets)} WHERE id = :oid"), params)
        await db.commit()
    return {"updated": True}


@router.delete("/organizations/{org_id}")
async def delete_organization(
    org_id: UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(text("DELETE FROM organizations WHERE id = :oid"), {"oid": org_id})
    await db.commit()
    return {"deleted": True}


@router.get("/organizations/{org_id}/quotas")
async def get_org_quotas(
    org_id: UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(text("SELECT * FROM organization_quotas WHERE organization_id = :oid"), {"oid": org_id})).first()
    return {"quotas": dict(row._mapping) if row else {}}


@router.put("/organizations/{org_id}/quotas")
async def update_org_quotas(
    org_id: UUID,
    data: dict[str, int],
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    sets = []
    params = {"oid": org_id}
    for field in ("max_imports_per_day", "max_storage_gb", "max_exports_per_day", "analytics_retention_days", "max_users"):
        if field in data:
            sets.append(f"{field} = :{field}")
            params[field] = data[field]
    if sets:
        sets.append("updated_at = NOW()")
        await db.execute(text(f"UPDATE organization_quotas SET {', '.join(sets)} WHERE organization_id = :oid"), params)
        await db.commit()
    return {"updated": True}


@router.get("/organizations/{org_id}/users")
async def list_org_users(
    org_id: UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        text("SELECT id, email, display_name, role, is_active, created_at FROM users WHERE organization_id = :oid ORDER BY display_name"),
        {"oid": org_id},
    )).mappings().all()
    return {"users": [dict(r) for r in rows], "total": len(rows)}
