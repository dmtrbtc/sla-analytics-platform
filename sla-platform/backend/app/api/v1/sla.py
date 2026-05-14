from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, sync_session_factory
from app.domain.models import SLADefinition, SLAMetric, TicketSnapshot
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("/definitions")
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


@router.post("/definitions")
async def create_sla_definition(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    required = ["name", "response_target_seconds", "resolution_target_seconds"]
    for field in required:
        if field not in payload:
            raise HTTPException(400, detail=f"Missing required field: {field}")

    sd = SLADefinition(
        name=payload["name"],
        queue_pattern=payload.get("queue_pattern", "*"),
        priority=payload.get("priority"),
        response_target_seconds=payload["response_target_seconds"],
        resolution_target_seconds=payload["resolution_target_seconds"],
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
    return {"definition": _sla_def_to_dict(sd)}


@router.get("/definitions/{definition_id}")
async def get_sla_definition(
    definition_id: int,
    db: AsyncSession = Depends(get_db),
):
    sd = await db.get(SLADefinition, definition_id)
    if not sd:
        raise HTTPException(404, detail="SLA definition not found")
    return {"definition": _sla_def_to_dict(sd)}


@router.put("/definitions/{definition_id}")
async def update_sla_definition(
    definition_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
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

    await db.flush()
    await db.refresh(sd)
    _sync_audit("sla_definition_updated", "sla_definition", str(sd.id), details={"name": sd.name})
    return {"definition": _sla_def_to_dict(sd)}


@router.delete("/definitions/{definition_id}")
async def delete_sla_definition(
    definition_id: int,
    db: AsyncSession = Depends(get_db),
):
    sd = await db.get(SLADefinition, definition_id)
    if not sd:
        raise HTTPException(404, detail="SLA definition not found")
    await db.delete(sd)
    _sync_audit("sla_definition_deleted", "sla_definition", str(definition_id), details={"name": sd.name})
    return {"status": "deleted"}


@router.get("/metrics")
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


@router.get("/breaches")
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


@router.get("/summary")
async def sla_summary(
    import_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    where = [SLAMetric.metric_name != None]
    if import_id:
        where.append(SLAMetric.import_id == import_id)

    total_q = select(func.count(SLAMetric.id)).where(*where)
    total = (await db.execute(total_q)).scalar() or 0

    breached_q = select(func.count(SLAMetric.id)).where(
        SLAMetric.sla_breached == True, *where[1:] if import_id else []
    )
    if import_id:
        breached_q = breached_q.where(SLAMetric.import_id == import_id)
    breached = (await db.execute(breached_q)).scalar() or 0

    response_q = select(func.count(SLAMetric.id)).where(
        SLAMetric.metric_name.in_(["response", "response_time"]), *where[1:] if import_id else []
    )
    if import_id:
        response_q = response_q.where(SLAMetric.import_id == import_id)
    response_count = (await db.execute(response_q)).scalar() or 0

    resolution_q = select(func.count(SLAMetric.id)).where(
        SLAMetric.metric_name.in_(["resolution", "resolution_time"]), *where[1:] if import_id else []
    )
    if import_id:
        resolution_q = resolution_q.where(SLAMetric.import_id == import_id)
    resolution_count = (await db.execute(resolution_q)).scalar() or 0

    return {
        "total_metrics": total,
        "total_breached": breached,
        "breach_rate": round(breached / total * 100, 2) if total else 0.0,
        "response_count": response_count,
        "resolution_count": resolution_count,
    }


def _sync_audit(action: str, resource_type: str, resource_id: str, details: Optional[dict] = None) -> None:
    try:
        sync_db = sync_session_factory()
        AuditService.log(sync_db, action=action, resource_type=resource_type, resource_id=resource_id, details=details)
        sync_db.close()
    except Exception:
        pass


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
