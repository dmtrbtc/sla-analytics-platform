import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, case, select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, sync_session_factory
from app.core.dependencies import require_admin
from app.domain.models import (
    BusinessCalendar,
    SLADefinition,
    SLAEscalationRule,
    SLAMetric,
    SLAQueueRule,
    TicketSnapshot,
    User,
)
from app.domain.schemas import (
    BusinessCalendarCreate,
    BusinessCalendarUpdate,
    SLADefinitionResponse,
    SLAEscalationRuleCreate,
    SLAEscalationRuleUpdate,
    SLAQueueRuleCreate,
    SLAQueueRuleUpdate,
    SLASimulateRequest,
)
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/definitions", response_model=dict)
async def list_sla_definitions(
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(SLADefinition)
    if is_active is not None:
        q = q.where(SLADefinition.is_active == is_active)
    q = q.order_by(SLADefinition.name)
    result = await db.execute(q)
    defs = result.scalars().all()
    return {"definitions": [_sla_def_to_dict(d) for d in defs]}


@router.post("/definitions", response_model=SLADefinitionResponse, status_code=201)
async def create_sla_definition(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    required = ["name", "metric_type", "warning_seconds", "critical_seconds"]
    for field in required:
        if field not in payload:
            raise HTTPException(400, detail=f"Missing required field: {field}")

    sd = SLADefinition(
        name=payload["name"],
        queue_pattern=payload.get("queue_pattern", "*"),
        priority=payload.get("priority"),
        response_target_seconds=payload["warning_seconds"],
        resolution_target_seconds=payload["critical_seconds"],
        pause_on_pending=payload.get("pause_on_pending", True),
        business_hours_only=payload.get("business_hours_only", False),
        business_hours=payload.get("business_hours"),
        is_active=payload.get("is_active", True),
        created_at=datetime.now(timezone.utc),
    )
    db.add(sd)
    await db.flush()
    await db.refresh(sd)
    _sync_audit("sla_definition_created", "sla_definition", str(sd.id), details={"name": sd.name})
    return {
        "id": sd.id,
        "name": sd.name,
        "description": payload.get("description"),
        "metric_type": payload["metric_type"],
        "warning_seconds": sd.response_target_seconds,
        "critical_seconds": sd.resolution_target_seconds,
        "is_active": sd.is_active,
        "business_hours_only": sd.business_hours_only,
        "created_at": sd.created_at,
        "updated_at": None,
    }


@router.get("/definitions/{definition_id}", response_model=SLADefinitionResponse)
async def get_sla_definition(
    definition_id: int,
    db: AsyncSession = Depends(get_db),
):
    sd = await db.get(SLADefinition, definition_id)
    if not sd:
        raise HTTPException(404, detail="SLA definition not found")
    return {
        "id": sd.id,
        "name": sd.name,
        "description": None,
        "metric_type": "response_time",
        "warning_seconds": sd.response_target_seconds,
        "critical_seconds": sd.resolution_target_seconds,
        "is_active": sd.is_active,
        "business_hours_only": sd.business_hours_only,
        "created_at": sd.created_at,
        "updated_at": None,
    }


@router.put("/definitions/{definition_id}", response_model=SLADefinitionResponse)
async def update_sla_definition(
    definition_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    sd = await db.get(SLADefinition, definition_id)
    if not sd:
        raise HTTPException(404, detail="SLA definition not found")

    for field in (
        "name", "queue_pattern", "priority",
        "response_target_seconds", "resolution_target_seconds",
        "pause_on_pending", "business_hours_only", "business_hours",
        "is_active",
    ):
        if field in payload:
            setattr(sd, field, payload[field])
    if "warning_seconds" in payload:
        sd.response_target_seconds = payload["warning_seconds"]
    if "critical_seconds" in payload:
        sd.resolution_target_seconds = payload["critical_seconds"]

    await db.flush()
    await db.refresh(sd)
    _sync_audit("sla_definition_updated", "sla_definition", str(sd.id), details={"name": sd.name})
    return {
        "id": sd.id,
        "name": sd.name,
        "description": payload.get("description"),
        "metric_type": payload.get("metric_type", "response_time"),
        "warning_seconds": sd.response_target_seconds,
        "critical_seconds": sd.resolution_target_seconds,
        "is_active": sd.is_active,
        "business_hours_only": sd.business_hours_only,
        "created_at": sd.created_at,
        "updated_at": None,
    }


@router.delete("/definitions/{definition_id}", response_model=dict)
async def delete_sla_definition(
    definition_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    sd = await db.get(SLADefinition, definition_id)
    if not sd:
        raise HTTPException(404, detail="SLA definition not found")
    await db.delete(sd)
    _sync_audit("sla_definition_deleted", "sla_definition", str(definition_id), details={"name": sd.name})
    return {"status": "deleted"}


@router.get("/metrics", response_model=dict)
async def list_sla_metrics(
    ticket_id: Optional[int] = Query(None),
    metric_name: Optional[str] = Query(None),
    sla_breached: Optional[bool] = Query(None),
    import_id: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    q = select(SLAMetric)
    if ticket_id is not None:
        q = q.where(SLAMetric.ticket_id == ticket_id)
    if metric_name:
        q = q.where(SLAMetric.metric_name == metric_name)
    if sla_breached is not None:
        q = q.where(SLAMetric.sla_breached == sla_breached)
    if import_id:
        q = q.where(SLAMetric.import_id == import_id)
    q = q.order_by(desc(SLAMetric.computed_at)).offset(offset).limit(limit)

    result = await db.execute(q)
    metrics = result.scalars().all()

    count_q = select(func.count(SLAMetric.id))
    if ticket_id is not None:
        count_q = count_q.where(SLAMetric.ticket_id == ticket_id)
    if metric_name:
        count_q = count_q.where(SLAMetric.metric_name == metric_name)
    if sla_breached is not None:
        count_q = count_q.where(SLAMetric.sla_breached == sla_breached)
    if import_id:
        count_q = count_q.where(SLAMetric.import_id == import_id)
    total = (await db.execute(count_q)).scalar()

    return {
        "metrics": [_sla_metric_to_dict(m) for m in metrics],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/breaches", response_model=dict)
async def list_sla_breaches(
    import_id: Optional[str] = Query(None),
    metric_name: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    q = select(SLAMetric).where(SLAMetric.sla_breached == True)
    if import_id:
        q = q.where(SLAMetric.import_id == import_id)
    if metric_name:
        q = q.where(SLAMetric.metric_name == metric_name)
    q = q.order_by(desc(SLAMetric.computed_at)).offset(offset).limit(limit)

    result = await db.execute(q)
    metrics = result.scalars().all()

    count_q = select(func.count(SLAMetric.id)).where(SLAMetric.sla_breached == True)
    if import_id:
        count_q = count_q.where(SLAMetric.import_id == import_id)
    if metric_name:
        count_q = count_q.where(SLAMetric.metric_name == metric_name)
    total = (await db.execute(count_q)).scalar()

    return {
        "breaches": [_sla_metric_to_dict(m) for m in metrics],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/summary", response_model=dict)
async def sla_summary(
    import_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    where = [SLAMetric.metric_name != None]
    if import_id:
        where.append(SLAMetric.import_id == import_id)

    row = (
        await db.execute(
            select(
                func.count(SLAMetric.id).label("total"),
                func.sum(case((SLAMetric.sla_breached == True, 1), else_=0)).label("breached"),
                func.sum(
                    case((SLAMetric.metric_name.in_(["response", "response_time"]), 1), else_=0)
                ).label("response_count"),
                func.sum(
                    case((SLAMetric.metric_name.in_(["resolution", "resolution_time"]), 1), else_=0)
                ).label("resolution_count"),
            ).where(*where)
        )
    ).one()

    total = row[0] or 0
    breached = row[1] or 0
    response_count = row[2] or 0
    resolution_count = row[3] or 0

    return {
        "total_metrics": total,
        "total_breached": breached,
        "breach_rate": round(breached / total * 100, 2) if total else 0.0,
        "response_count": response_count,
        "resolution_count": resolution_count,
    }


# ── Queue-level SLA Rules CRUD ──


@router.get("/queue-rules", response_model=dict)
async def list_queue_rules(
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(SLAQueueRule)
    if is_active is not None:
        q = q.where(SLAQueueRule.is_active == is_active)
    q = q.order_by(SLAQueueRule.priority.desc().nullslast(), SLAQueueRule.name)
    result = await db.execute(q)
    rules = result.scalars().all()
    return {"queue_rules": [_queue_rule_to_dict(r) for r in rules]}


@router.post("/queue-rules", response_model=dict, status_code=201)
async def create_queue_rule(
    payload: SLAQueueRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    rule = SLAQueueRule(
        name=payload.name,
        queue_pattern=payload.queue_pattern,
        priority=payload.priority,
        response_target_seconds=payload.response_target_seconds,
        resolution_target_seconds=payload.resolution_target_seconds,
        calendar_id=payload.calendar_id,
        is_active=payload.is_active,
        description=payload.description,
        created_by=current_user.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    _sync_audit("queue_rule_created", "sla_queue_rule", str(rule.id), details={"name": rule.name})
    return {"queue_rule": _queue_rule_to_dict(rule)}


@router.get("/queue-rules/{rule_id}", response_model=dict)
async def get_queue_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    rule = await db.get(SLAQueueRule, rule_id)
    if not rule:
        raise HTTPException(404, detail="Queue SLA rule not found")
    return {"queue_rule": _queue_rule_to_dict(rule)}


@router.put("/queue-rules/{rule_id}", response_model=dict)
async def update_queue_rule(
    rule_id: UUID,
    payload: SLAQueueRuleUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    rule = await db.get(SLAQueueRule, rule_id)
    if not rule:
        raise HTTPException(404, detail="Queue SLA rule not found")

    update_fields = {
        "name", "queue_pattern", "priority",
        "response_target_seconds", "resolution_target_seconds",
        "calendar_id", "is_active", "description",
    }
    for field in update_fields:
        val = getattr(payload, field, None)
        if val is not None:
            setattr(rule, field, val)
    rule.updated_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(rule)
    _sync_audit("queue_rule_updated", "sla_queue_rule", str(rule.id), details={"name": rule.name})
    return {"queue_rule": _queue_rule_to_dict(rule)}


@router.delete("/queue-rules/{rule_id}", response_model=dict)
async def delete_queue_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    rule = await db.get(SLAQueueRule, rule_id)
    if not rule:
        raise HTTPException(404, detail="Queue SLA rule not found")
    await db.delete(rule)
    _sync_audit("queue_rule_deleted", "sla_queue_rule", str(rule_id), details={"name": rule.name})
    return {"status": "deleted"}


# ── Queue Breaches Aggregation ──


@router.get("/queue-breaches", response_model=dict)
async def list_queue_breaches(
    import_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    where = [SLAMetric.queue_name.isnot(None), SLAMetric.queue_name != ""]
    if import_id:
        where.append(SLAMetric.import_id == import_id)

    rows = (
        await db.execute(
            select(
                SLAMetric.queue_name,
                func.count(func.distinct(SLAMetric.ticket_id)).label("tickets_total"),
                func.sum(
                    case(
                        (
                            and_(
                                SLAMetric.metric_name.in_(["response_time", "response"]),
                                SLAMetric.sla_breached == True,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("breached_response"),
                func.sum(
                    case(
                        (
                            and_(
                                SLAMetric.metric_name.in_(["resolution_time", "resolution"]),
                                SLAMetric.sla_breached == True,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("breached_resolution"),
                func.avg(
                    case(
                        (
                            SLAMetric.metric_name.in_(["response_time", "response"]),
                            SLAMetric.metric_seconds,
                        ),
                    )
                ).label("avg_response_seconds"),
                func.avg(
                    case(
                        (
                            SLAMetric.metric_name.in_(["resolution_time", "resolution"]),
                            SLAMetric.metric_seconds,
                        ),
                    )
                ).label("avg_resolution_seconds"),
            )
            .where(*where)
            .group_by(SLAMetric.queue_name)
            .order_by(
                func.sum(
                    case(
                        (
                            and_(
                                SLAMetric.metric_name.in_(["response_time", "resolution_time", "response", "resolution"]),
                                SLAMetric.sla_breached == True,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).desc()
            )
        )
    ).all()

    return {
        "queue_breaches": [
            {
                "queue_name": r[0],
                "tickets_total": r[1] or 0,
                "breached_response": r[2] or 0,
                "breached_resolution": r[3] or 0,
                "avg_response_minutes": round(float(r[4]) / 60, 2) if r[4] else 0.0,
                "avg_resolution_hours": round(float(r[5]) / 3600, 2) if r[5] else 0.0,
            }
            for r in rows
        ]
    }


# ── Business Calendars CRUD ──


@router.get("/calendars", response_model=dict)
async def list_calendars(
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(BusinessCalendar)
    if is_active is not None:
        q = q.where(BusinessCalendar.is_active == is_active)
    q = q.order_by(BusinessCalendar.name)
    result = await db.execute(q)
    calendars = result.scalars().all()
    return {"calendars": [_calendar_to_dict(c) for c in calendars]}


@router.post("/calendars", response_model=dict, status_code=201)
async def create_calendar(
    payload: BusinessCalendarCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    cal = BusinessCalendar(
        name=payload.name,
        timezone=payload.timezone,
        workdays=payload.workdays,
        start_time=payload.start_time,
        end_time=payload.end_time,
        holidays_json=payload.holidays_json,
        is_24x7=payload.is_24x7,
        is_active=payload.is_active,
        description=payload.description,
        created_by=current_user.id,
    )
    db.add(cal)
    await db.flush()
    await db.refresh(cal)
    return {"calendar": _calendar_to_dict(cal)}


@router.get("/calendars/{calendar_id}", response_model=dict)
async def get_calendar(
    calendar_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    cal = await db.get(BusinessCalendar, calendar_id)
    if not cal:
        raise HTTPException(404, detail="Calendar not found")
    return {"calendar": _calendar_to_dict(cal)}


@router.put("/calendars/{calendar_id}", response_model=dict)
async def update_calendar(
    calendar_id: UUID,
    payload: BusinessCalendarUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    cal = await db.get(BusinessCalendar, calendar_id)
    if not cal:
        raise HTTPException(404, detail="Calendar not found")
    for field in ("name", "timezone", "workdays", "start_time", "end_time", "holidays_json", "is_24x7", "is_active", "description"):
        val = getattr(payload, field, None)
        if val is not None:
            setattr(cal, field, val)
    cal.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(cal)
    return {"calendar": _calendar_to_dict(cal)}


@router.delete("/calendars/{calendar_id}", response_model=dict)
async def delete_calendar(
    calendar_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    cal = await db.get(BusinessCalendar, calendar_id)
    if not cal:
        raise HTTPException(404, detail="Calendar not found")
    await db.delete(cal)
    return {"status": "deleted"}


# ── SLA Escalation Rules CRUD ──


@router.get("/escalations", response_model=dict)
async def list_escalations(
    sla_rule_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(SLAEscalationRule)
    if sla_rule_id:
        q = q.where(SLAEscalationRule.sla_rule_id == sla_rule_id)
    q = q.order_by(SLAEscalationRule.threshold_percent)
    result = await db.execute(q)
    rules = result.scalars().all()
    return {"escalations": [_escalation_to_dict(r) for r in rules]}


@router.post("/escalations", response_model=dict, status_code=201)
async def create_escalation(
    payload: SLAEscalationRuleCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    # Verify SLA rule exists
    sla_rule = await db.get(SLAQueueRule, payload.sla_rule_id)
    if not sla_rule:
        raise HTTPException(404, detail="SLA queue rule not found")
    rule = SLAEscalationRule(
        sla_rule_id=payload.sla_rule_id,
        threshold_percent=payload.threshold_percent,
        severity=payload.severity,
        notify_email=payload.notify_email,
        notify_telegram=payload.notify_telegram,
        webhook_url=payload.webhook_url,
        is_active=payload.is_active,
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return {"escalation": _escalation_to_dict(rule)}


@router.get("/escalations/{rule_id}", response_model=dict)
async def get_escalation(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    rule = await db.get(SLAEscalationRule, rule_id)
    if not rule:
        raise HTTPException(404, detail="Escalation rule not found")
    return {"escalation": _escalation_to_dict(rule)}


@router.put("/escalations/{rule_id}", response_model=dict)
async def update_escalation(
    rule_id: UUID,
    payload: SLAEscalationRuleUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    rule = await db.get(SLAEscalationRule, rule_id)
    if not rule:
        raise HTTPException(404, detail="Escalation rule not found")
    for field in ("threshold_percent", "severity", "notify_email", "notify_telegram", "webhook_url", "is_active"):
        val = getattr(payload, field, None)
        if val is not None:
            setattr(rule, field, val)
    rule.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(rule)
    return {"escalation": _escalation_to_dict(rule)}


@router.delete("/escalations/{rule_id}", response_model=dict)
async def delete_escalation(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    rule = await db.get(SLAEscalationRule, rule_id)
    if not rule:
        raise HTTPException(404, detail="Escalation rule not found")
    await db.delete(rule)
    return {"status": "deleted"}


# ── SLA Simulator ──


@router.post("/simulate", response_model=dict)
async def simulate_sla(
    payload: SLASimulateRequest,
    db: AsyncSession = Depends(get_db),
):
    from app.services.sla.risk_engine import risk_level_from_ratio, risk_score_from_ratio

    resp_ratio = 0.5  # simulate at 50% by default
    res_ratio = 0.5

    # If a calendar is specified, compute simulated business-time ratio
    if payload.calendar_id:
        cal = await db.get(BusinessCalendar, payload.calendar_id)
        if cal and not cal.is_24x7:
            work_hours = 0
            total_hours = 0
            for day, work in (cal.workdays or {}).items():
                if work:
                    start_h, start_m = (cal.start_time or "09:00").split(":")
                    end_h, end_m = (cal.end_time or "18:00").split(":")
                    day_hours = (int(end_h) * 60 + int(end_m) - int(start_h) * 60 - int(start_m)) / 60
                    work_hours += max(day_hours, 0)
                total_hours += 24
            effective_ratio = work_hours / total_hours if total_hours else 1.0
            resp_ratio = min(1.0, resp_ratio / effective_ratio) if effective_ratio > 0 else 1.0
            res_ratio = min(1.0, res_ratio / effective_ratio) if effective_ratio > 0 else 1.0

    resp_breached = resp_ratio >= 1.0
    res_breached = res_ratio >= 1.0
    overall_ratio = max(resp_ratio, res_ratio)

    return {
        "queue_name": payload.queue_name,
        "response_target_seconds": payload.response_target_seconds,
        "resolution_target_seconds": payload.resolution_target_seconds,
        "will_breach_response": resp_breached,
        "will_breach_resolution": res_breached,
        "risk_level": risk_level_from_ratio(overall_ratio),
        "risk_score": risk_score_from_ratio(overall_ratio),
        "simulated_response_ratio": round(resp_ratio, 4),
        "simulated_resolution_ratio": round(res_ratio, 4),
    }


def _sync_audit(action: str, resource_type: str, resource_id: str, details: Optional[dict] = None) -> None:
    try:
        sync_db = sync_session_factory()
        AuditService.log(sync_db, action=action, resource_type=resource_type, resource_id=resource_id, details=details)
        sync_db.close()
    except Exception:
        logger.warning("Audit log failed for %s %s %s", action, resource_type, resource_id, exc_info=True)


def _sla_def_to_dict(sd: SLADefinition) -> dict:
    return {
        "id": sd.id,
        "name": sd.name,
        "queue_pattern": sd.queue_pattern,
        "priority": sd.priority,
        "response_target_seconds": sd.response_target_seconds,
        "resolution_target_seconds": sd.resolution_target_seconds,
        "pause_on_pending": sd.pause_on_pending,
        "business_hours_only": sd.business_hours_only,
        "business_hours": sd.business_hours,
        "is_active": sd.is_active,
        "created_at": sd.created_at.isoformat() if sd.created_at else None,
    }


def _sla_metric_to_dict(m: SLAMetric) -> dict:
    return {
        "id": m.id,
        "ticket_id": m.ticket_id,
        "metric_name": m.metric_name,
        "metric_seconds": m.metric_seconds,
        "sla_breached": m.sla_breached,
        "sla_risk_score": m.sla_risk_score,
        "risk_level": m.risk_level,
        "risk_reason": m.risk_reason,
        "queue_name": m.queue_name,
        "owner": m.owner,
        "team_prefix": m.team_prefix,
        "sla_definition_id": m.sla_definition_id,
        "import_id": str(m.import_id) if m.import_id else None,
        "confidence": m.confidence,
        "computed_at": m.computed_at.isoformat() if m.computed_at else None,
    }


def _calendar_to_dict(c: BusinessCalendar) -> dict:
    return {
        "id": str(c.id),
        "name": c.name,
        "timezone": c.timezone or "UTC",
        "workdays": c.workdays or {},
        "start_time": c.start_time or "09:00",
        "end_time": c.end_time or "18:00",
        "holidays_json": c.holidays_json or [],
        "is_24x7": c.is_24x7 or False,
        "is_active": c.is_active,
        "description": c.description,
        "created_by": str(c.created_by) if c.created_by else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def _escalation_to_dict(r: SLAEscalationRule) -> dict:
    return {
        "id": str(r.id),
        "sla_rule_id": str(r.sla_rule_id),
        "threshold_percent": r.threshold_percent,
        "severity": r.severity,
        "notify_email": r.notify_email,
        "notify_telegram": r.notify_telegram,
        "webhook_url": r.webhook_url,
        "is_active": r.is_active,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


# ── SLA V2 Enterprise Endpoints ──


@router.get("/timeline/{ticket_id}", response_model=dict)
async def get_ticket_sla_timeline(
    ticket_id: int,
    import_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Return full SLA timeline explanation for a ticket.

    Shows queue intervals, owner intervals, pending intervals,
    working intervals, metrics, and where time was lost.
    """
    from app.services.sla_engine import SLAEngine
    from app.services.sla.timeline_engine import build_timeline

    if import_id is None:
        row = (
            await db.execute(
                select(TicketSnapshot.last_import_id)
                .where(TicketSnapshot.ticket_id == ticket_id)
            )
        ).scalar()
        if not row:
            raise HTTPException(404, detail="Ticket not found")
        import_id = str(row)

    sync_db = sync_session_factory()
    try:
        explanation = SLAEngine.explain_ticket_sla(sync_db, ticket_id, import_id)
    finally:
        sync_db.close()

    return explanation


@router.get("/efficiency", response_model=dict)
async def list_sla_efficiency(
    import_id: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List SLA efficiency metrics (sla_efficiency_pct metrics)."""
    q = select(SLAMetric).where(SLAMetric.metric_name == "sla_efficiency_pct")
    if import_id:
        q = q.where(SLAMetric.import_id == import_id)
    q = q.order_by(desc(SLAMetric.metric_seconds)).offset(offset).limit(limit)
    result = await db.execute(q)
    metrics = result.scalars().all()
    return {
        "metrics": [_sla_metric_to_dict(m) for m in metrics],
        "total": len(metrics),
    }


@router.get("/predictive/breach-eta", response_model=dict)
async def get_breach_eta(
    ticket_id: int = Query(...),
    metric_name: str = Query("first_response_time"),
    db: AsyncSession = Depends(get_db),
):
    """Compute breach ETA and probability for a ticket's metric."""
    from app.services.sla.predictive_engine import compute_breach_eta

    metric = (
        await db.execute(
            select(SLAMetric).where(
                SLAMetric.ticket_id == ticket_id,
                SLAMetric.metric_name == metric_name,
            ).order_by(desc(SLAMetric.computed_at)).limit(1)
        )
    ).scalar_one_or_none()

    if not metric:
        raise HTTPException(404, detail="No SLA metric found for this ticket")

    target = metric.metric_seconds or 0
    eta = compute_breach_eta(metric.metric_seconds or 0, max(target, 1))
    return {
        "ticket_id": ticket_id,
        "metric_name": metric_name,
        "current_seconds": metric.metric_seconds,
        "target_seconds": target,
        "prediction": eta,
    }


@router.get("/predictive/queue-overload", response_model=dict)
async def get_queue_overload(
    queue_name: str = Query(...),
    lookback_hours: int = Query(24, ge=1, le=168),
):
    """Compute overload score for a queue."""
    from app.services.sla.predictive_engine import compute_queue_overload
    sync_db = sync_session_factory()
    try:
        result = compute_queue_overload(sync_db, queue_name, lookback_hours)
    finally:
        sync_db.close()
    return result


@router.get("/v2/metrics", response_model=dict)
async def list_v2_metrics(
    ticket_id: Optional[int] = Query(None),
    metric_name: Optional[str] = Query(None),
    sla_breached: Optional[bool] = Query(None),
    import_id: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    team_prefix: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """V2 metrics listing with risk_level and team_prefix filters."""
    q = select(SLAMetric)
    if ticket_id is not None:
        q = q.where(SLAMetric.ticket_id == ticket_id)
    if metric_name:
        q = q.where(SLAMetric.metric_name == metric_name)
    if sla_breached is not None:
        q = q.where(SLAMetric.sla_breached == sla_breached)
    if import_id:
        q = q.where(SLAMetric.import_id == import_id)
    if risk_level:
        q = q.where(SLAMetric.risk_level == risk_level)
    if team_prefix:
        q = q.where(SLAMetric.team_prefix == team_prefix)
    q = q.order_by(desc(SLAMetric.computed_at)).offset(offset).limit(limit)
    result = await db.execute(q)
    metrics = result.scalars().all()
    return {
        "metrics": [_sla_metric_to_dict(m) for m in metrics],
        "total": len(metrics),
    }


def _queue_rule_to_dict(r: SLAQueueRule) -> dict:
    return {
        "id": str(r.id),
        "name": r.name,
        "queue_pattern": r.queue_pattern,
        "priority": r.priority or 0,
        "response_target_seconds": r.response_target_seconds,
        "resolution_target_seconds": r.resolution_target_seconds,
        "calendar_id": str(r.calendar_id) if r.calendar_id else None,
        "is_active": r.is_active,
        "description": r.description,
        "created_by": str(r.created_by) if r.created_by else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }
