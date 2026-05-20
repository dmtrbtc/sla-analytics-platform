"""Billing + Subscriptions API — plans, usage, quotas, billing analytics."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db, sync_session_factory
from app.core.dependencies import get_current_user, require_admin
from app.domain.models import User
from app.services.billing.usage import (
    get_org_plan, check_quota, record_usage, get_billing_analytics,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/plans")
async def list_plans(_: User = Depends(get_current_user)):
    db = sync_session_factory()
    try:
        rows = db.execute(text("SELECT * FROM subscription_plans WHERE is_active = True ORDER BY price_monthly_cents")).mappings().all()
        return {"plans": [dict(r) for r in rows], "total": len(rows)}
    finally:
        db.close()


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: UUID, _: User = Depends(get_current_user)):
    db = sync_session_factory()
    try:
        row = db.execute(text("SELECT * FROM subscription_plans WHERE id = :pid"), {"pid": plan_id}).first()
        if not row:
            raise HTTPException(status_code=404, detail="Plan not found")
        return {"plan": dict(row._mapping)}
    finally:
        db.close()


@router.get("/org/{org_id}/subscription")
async def get_org_subscription(org_id: UUID, _: User = Depends(require_admin)):
    plan = get_org_plan(org_id)
    if not plan:
        raise HTTPException(status_code=404, detail="No active subscription")
    return {"subscription": plan}


@router.post("/org/{org_id}/subscription")
async def update_org_subscription(org_id: UUID, data: dict[str, Any], _: User = Depends(require_admin)):
    db = sync_session_factory()
    try:
        plan_id = data.get("plan_id")
        from app.services.billing.models import OrganizationSubscription
        import uuid

        existing = db.query(OrganizationSubscription).filter(
            OrganizationSubscription.organization_id == org_id,
            OrganizationSubscription.status.in_(["active", "trialing"]),
        ).first()

        if existing:
            existing.plan_id = UUID(plan_id) if isinstance(plan_id, str) else plan_id
            existing.current_period_end = __import__("datetime").datetime.now(__import__("timezone").utc) + __import__("datetime").timedelta(days=30)
        else:
            now = __import__("datetime").datetime.now(__import__("timezone").utc)
            sub = OrganizationSubscription(
                organization_id=org_id,
                plan_id=UUID(plan_id) if isinstance(plan_id, str) else plan_id,
                status="active",
                current_period_start=now,
                current_period_end=now + __import__("datetime").timedelta(days=30),
            )
            db.add(sub)
        db.commit()
        return {"updated": True}
    finally:
        db.close()


@router.get("/org/{org_id}/usage")
async def get_usage(org_id: UUID, metric: str = Query(None), _: User = Depends(require_admin)):
    if metric:
        return check_quota(org_id, metric)
    return get_billing_analytics(org_id)


@router.post("/org/{org_id}/usage/record")
async def record_usage_event(org_id: UUID, data: dict[str, Any], _: User = Depends(require_admin)):
    record_usage(org_id, data.get("metric", "api_call"), data.get("value", 1))
    return {"recorded": True}


@router.get("/billing/analytics")
async def billing_analytics(_: User = Depends(require_admin)):
    return get_billing_analytics()
