"""Advanced RBAC API — permission groups, role management, permission checks."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, sync_session_factory
from app.core.dependencies import get_current_user, require_admin
from app.domain.models import User
from app.services.rbac.permissions import (
    has_permission, get_user_permissions, get_role_permissions,
    PERMISSION_MATRIX, ACCESS_GROUPS,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/permissions")
async def list_permissions(current_user: User = Depends(get_current_user)):
    return {
        "all_permissions": sorted(PERMISSION_MATRIX.keys()),
        "user_permissions": get_user_permissions(current_user),
        "role": current_user.role,
    }


@router.get("/permissions/check")
async def check_permission(
    permission: str = Query(..., description="Permission to check"),
    current_user: User = Depends(get_current_user),
):
    return {
        "permission": permission,
        "granted": has_permission(current_user, permission),
        "role": current_user.role,
    }


@router.get("/roles/{role}/permissions")
async def role_permissions(role: str, _: User = Depends(require_admin)):
    if role not in ["admin", "analyst", "team_lead", "viewer"]:
        raise HTTPException(status_code=404, detail="Unknown role")
    return {"role": role, "permissions": get_role_permissions(role)}


@router.put("/users/{user_id}/role")
async def update_user_role(user_id: str, data: dict, current_user: User = Depends(require_admin)):
    new_role = data.get("role")
    if new_role not in ["admin", "analyst", "team_lead", "viewer"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    db = sync_session_factory()
    try:
        db.execute(text("UPDATE users SET role = :role WHERE id = :uid"), {"role": new_role, "uid": user_id})
        db.commit()
        return {"updated": True, "role": new_role}
    finally:
        db.close()


@router.get("/users/{user_id}/permissions")
async def user_permissions(user_id: str, _: User = Depends(require_admin)):
    db = sync_session_factory()
    try:
        row = db.execute(text("SELECT * FROM users WHERE id = :uid"), {"uid": user_id}).first()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        user = User(id=row.id, email=row.email, display_name=row.display_name, role=row.role, is_active=row.is_active)
        return {
            "user_id": user_id,
            "role": row.role,
            "permissions": get_user_permissions(user),
        }
    finally:
        db.close()
