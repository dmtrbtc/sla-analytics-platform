import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, case, select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, sync_session_factory
from app.core.dependencies import require_admin
from app.domain.models import SLADefinition, SLAMetric, SLAQueueRule, User
from app.domain.schemas import SLADefinitionResponse, SLAQueueRuleCreate, SLAQueueRuleUpdate
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
        "is_active", "description",
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
                func.count(SLAMetric.id).label("total"),
                func.sum(
                    case((SLAMetric.sla_breached == True, 1), else_=0)
                ).label("breached"),
                func.sum(
                    case(
                        (SLAMetric.metric_name.in_(["response_time", "response"]), 1),
                        else_=0,
                    )
                ).label("response_count"),
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
                ).label("response_breached"),
                func.sum(
                    case(
                        (SLAMetric.metric_name.in_(["resolution_time", "resolution"]), 1),
                        else_=0,
                    )
                ).label("resolution_count"),
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
                ).label("resolution_breached"),
                func.avg(SLAMetric.metric_seconds).label("avg_seconds"),
            )
            .where(*where)
            .group_by(SLAMetric.queue_name)
            .order_by(func.sum(
                case((SLAMetric.sla_breached == True, 1), else_=0)
            ).desc())
        )
    ).all()

    return {
        "queue_breaches": [
            {
                "queue": r[0],
                "total": r[1] or 0,
                "breached": r[2] or 0,
                "breach_rate": round((r[2] or 0) / (r[1] or 1) * 100, 2),
                "response_count": r[3] or 0,
                "response_breached": r[4] or 0,
                "resolution_count": r[5] or 0,
                "resolution_breached": r[6] or 0,
                "avg_seconds": round(float(r[7]), 2) if r[7] else 0.0,
            }
            for r in rows
        ]
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
        "queue_name": m.queue_name,
        "owner": m.owner,
        "team_prefix": m.team_prefix,
        "sla_definition_id": m.sla_definition_id,
        "import_id": str(m.import_id) if m.import_id else None,
        "confidence": m.confidence,
        "computed_at": m.computed_at.isoformat() if m.computed_at else None,
    }


def _queue_rule_to_dict(r: SLAQueueRule) -> dict:
    return {
        "id": str(r.id),
        "name": r.name,
        "queue_pattern": r.queue_pattern,
        "priority": r.priority or 0,
        "response_target_seconds": r.response_target_seconds,
        "resolution_target_seconds": r.resolution_target_seconds,
        "is_active": r.is_active,
        "description": r.description,
        "created_by": str(r.created_by) if r.created_by else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }
