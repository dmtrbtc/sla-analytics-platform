"""Enterprise security endpoints — audit chain, signed exports, security analytics."""
from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.dependencies import get_current_user, require_admin
from app.domain.models import User
from app.services.security.audit_chain import (
    append_audit_entry, verify_audit_chain, sign_export_data, verify_export_signature,
    analyze_security_events, detect_api_abuse,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.post("/audit/log")
async def log_audit_entry(
    data: dict,
    current_user: User = Depends(get_current_user),
):
    result = append_audit_entry(
        organization_id=data.get("organization_id"),
        actor_id=current_user.id,
        action=data["action"],
        resource_type=data.get("resource_type", "unknown"),
        resource_id=data.get("resource_id", ""),
        details=data.get("details", {}),
        ip_address=data.get("ip_address"),
    )
    return result


@router.get("/audit/chain/verify/{org_id}")
async def verify_chain(org_id: UUID, _: User = Depends(require_admin)):
    return verify_audit_chain(org_id)


@router.post("/exports/sign")
async def sign_export(data: dict, _: User = Depends(require_admin)):
    result = sign_export_data(data.get("data", ""), data.get("org_slug", ""))
    return {"signature": result}


@router.post("/exports/verify")
async def verify_export(data: dict, _: User = Depends(require_admin)):
    valid = verify_export_signature(data.get("data", ""), data.get("signature", ""), data.get("org_slug", ""))
    return {"valid": valid}


@router.get("/analytics/security")
async def security_analytics(days: int = Query(7, ge=1, le=90), _: User = Depends(require_admin)):
    return analyze_security_events(days=days)


@router.get("/analytics/abuse")
async def abuse_detection(threshold: int = Query(100, ge=10), _: User = Depends(require_admin)):
    return {"abusers": detect_api_abuse(max_requests_per_minute=threshold)}
