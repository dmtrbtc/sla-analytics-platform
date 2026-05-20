"""Usage tracking, quota enforcement, billing analytics."""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.database import sync_session_factory
from app.services.billing.models import SubscriptionPlan, OrganizationSubscription, UsageRecord

logger = logging.getLogger(__name__)


DEFAULT_PLANS = [
    {
        "name": "Free",
        "slug": "free",
        "description": "Для небольших команд до 5 пользователей",
        "price_monthly_cents": 0,
        "max_imports_per_day": 5,
        "max_storage_gb": 1,
        "max_exports_per_day": 2,
        "analytics_retention_days": 14,
        "max_users": 5,
        "max_queues": 5,
        "features": {"analytics": True, "ai_copilot": False, "api_access": False, "sso": False},
    },
    {
        "name": "Pro",
        "slug": "pro",
        "description": "Для растущих команд с расширенной аналитикой",
        "price_monthly_cents": 9900,  # $99
        "price_yearly_cents": 99000,  # $990
        "max_imports_per_day": 50,
        "max_storage_gb": 10,
        "max_exports_per_day": 20,
        "analytics_retention_days": 90,
        "max_users": 25,
        "max_queues": 50,
        "features": {"analytics": True, "ai_copilot": True, "api_access": True, "sso": False},
    },
    {
        "name": "Enterprise",
        "slug": "enterprise",
        "description": "Для крупных организаций с полным контролем",
        "price_monthly_cents": 49900,  # $499
        "price_yearly_cents": 499000,  # $4990
        "max_imports_per_day": 500,
        "max_storage_gb": 100,
        "max_exports_per_day": 200,
        "analytics_retention_days": 365,
        "max_users": 999,
        "max_queues": 999,
        "features": {"analytics": True, "ai_copilot": True, "api_access": True, "sso": True, "sla": True, "white_label": True},
    },
]


def seed_default_plans(db: Session) -> list[SubscriptionPlan]:
    """Create default subscription plans if they don't exist."""
    plans = []
    for plan_data in DEFAULT_PLANS:
        existing = db.query(SubscriptionPlan).filter(SubscriptionPlan.slug == plan_data["slug"]).first()
        if not existing:
            plan = SubscriptionPlan(**plan_data)
            db.add(plan)
            plans.append(plan)
        else:
            plans.append(existing)
    db.commit()
    return plans


def get_org_plan(organization_id: UUID) -> Optional[dict]:
    """Get active subscription plan for an organization."""
    db = sync_session_factory()
    try:
        sub = db.query(OrganizationSubscription).filter(
            OrganizationSubscription.organization_id == organization_id,
            OrganizationSubscription.status.in_(["active", "trialing"]),
        ).first()
        if not sub:
            return None
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == sub.plan_id).first()
        if not plan:
            return None
        return {
            "plan_name": plan.name,
            "plan_slug": plan.slug,
            "status": sub.status,
            "current_period_end": str(sub.current_period_end),
            "features": plan.features,
            "limits": {
                "max_imports_per_day": plan.max_imports_per_day,
                "max_storage_gb": plan.max_storage_gb,
                "max_exports_per_day": plan.max_exports_per_day,
                "analytics_retention_days": plan.analytics_retention_days,
                "max_users": plan.max_users,
                "max_queues": plan.max_queues,
            },
        }
    finally:
        db.close()


def record_usage(organization_id: UUID, metric: str, value: int = 1) -> None:
    """Record a usage event."""
    db = sync_session_factory()
    try:
        record = UsageRecord(
            organization_id=organization_id,
            metric=metric,
            value=value,
        )
        db.add(record)
        db.commit()
    except Exception as exc:
        logger.warning("Failed to record usage: %s", exc)
    finally:
        db.close()


def check_quota(organization_id: UUID, metric: str) -> dict:
    """Check if an organization has quota remaining."""
    db = sync_session_factory()
    try:
        plan = get_org_plan(organization_id)
        if not plan:
            return {"allowed": True, "remaining": 999}

        limits = plan["limits"]
        max_val = {"import": limits["max_imports_per_day"], "export": limits["max_exports_per_day"]}.get(metric, 999)
        if max_val <= 0:
            return {"allowed": False, "remaining": 0}

        since = datetime.now(timezone.utc) - timedelta(days=1)
        used = db.query(func.sum(UsageRecord.value)).filter(
            UsageRecord.organization_id == organization_id,
            UsageRecord.metric == metric,
            UsageRecord.recorded_at >= since,
        ).scalar() or 0

        remaining = max(0, max_val - used)
        return {"allowed": used < max_val, "used": used, "limit": max_val, "remaining": remaining}
    finally:
        db.close()


def get_billing_analytics(organization_id: Optional[UUID] = None) -> dict:
    """Return billing analytics for an organization or all."""
    db = sync_session_factory()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=30)

        if organization_id:
            usage = db.query(
                UsageRecord.metric,
                func.sum(UsageRecord.value).label("total"),
            ).filter(
                UsageRecord.organization_id == organization_id,
                UsageRecord.recorded_at >= since,
            ).group_by(UsageRecord.metric).all()
        else:
            usage = db.query(
                UsageRecord.metric,
                func.sum(UsageRecord.value).label("total"),
            ).filter(
                UsageRecord.recorded_at >= since,
            ).group_by(UsageRecord.metric).all()

        return {
            "period_days": 30,
            "usage": {r.metric: r.total for r in usage},
        }
    finally:
        db.close()
