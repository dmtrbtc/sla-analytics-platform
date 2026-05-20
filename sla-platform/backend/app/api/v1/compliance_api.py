"""Security + Compliance API — SAML, session security, export encryption, compliance dashboard."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, sync_session_factory
from app.core.dependencies import get_current_user, require_admin
from app.domain.models import User
from app.services.compliance.security_v2 import (
    generate_saml_metadata, register_saml_idp, validate_session_security,
    encrypt_export_data, decrypt_export_data,
    get_audit_retention_status, apply_audit_retention_policy,
    get_compliance_dashboard,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/compliance/dashboard")
async def compliance_dashboard(_: User = Depends(require_admin)):
    return get_compliance_dashboard()


@router.get("/saml/metadata")
async def saml_metadata(entity_id: str = Query(...), acs_url: str = Query(...)):
    return generate_saml_metadata(entity_id, acs_url, entity_id)


@router.post("/saml/providers")
async def register_idp(data: dict[str, Any], _: User = Depends(require_admin)):
    db = sync_session_factory()
    try:
        result = register_saml_idp(db, UUID(data["organization_id"]), data["metadata"])
        return result
    finally:
        db.close()


@router.post("/session/validate")
async def check_session(data: dict[str, Any], current_user: User = Depends(get_current_user)):
    db = sync_session_factory()
    try:
        return validate_session_security(db, current_user.id, data.get("ip", ""), data.get("user_agent", ""))
    finally:
        db.close()


@router.post("/exports/encrypt")
async def encrypt_export(data: dict[str, str], _: User = Depends(require_admin)):
    result = encrypt_export_data(data.get("data", ""))
    return result


@router.post("/exports/decrypt")
async def decrypt_export(data: dict[str, str], _: User = Depends(require_admin)):
    result = decrypt_export_data(data.get("data", ""))
    return result


@router.get("/audit/retention")
async def audit_retention(_: User = Depends(require_admin)):
    return get_audit_retention_status()


@router.post("/audit/retention/apply")
async def apply_retention(days: int = Query(90, ge=30), _: User = Depends(require_admin)):
    return apply_audit_retention_policy(retention_days=days)
