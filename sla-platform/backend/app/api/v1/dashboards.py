from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domain.models import (
    OwnershipPeriod,
    QueuePeriod,
    SLAMetric,
    SLADefinition,
    Team,
    TicketEvent,
    TicketSnapshot,
)
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get("/overview")
async def dashboard_overview(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    return await DashboardService.get_overview(db, days=days)


@router.get("/time-series")
async def time_series(
    metric: str = Query("tickets_created"),
    granularity: str = Query("daily"),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    data = await DashboardService.get_time_series(db, metric, granularity, days)
    return {"metric": metric, "granularity": granularity, "data": data}


@router.get("/teams")
async def teams_analytics(
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    return {"teams": await DashboardService.get_teams_analytics(db, days=days)}


@router.get("/ticket-flow")
async def ticket_flow(
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    return await DashboardService.get_ticket_flow(db, days=days)


@router.get("/sla-trend")
async def sla_trend(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    rows = (
        await db.execute(
            select(
                func.date_trunc("day", SLAMetric.computed_at).label("day"),
                func.count(SLAMetric.id),
                func.sum(SLAMetric.sla_breached.cast(type(1))),
            )
            .where(SLAMetric.computed_at >= since)
            .group_by(text("day"))
            .order_by(text("day"))
        )
    ).all()
    return {
        "trend": [
            {"date": str(r[0].date()), "total": r[1], "breached": r[2]}
            for r in rows
        ]
    }


@router.get("/by-queue")
async def by_queue(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(
                TicketSnapshot.current_queue,
                func.count(TicketSnapshot.ticket_id),
            )
            .group_by(TicketSnapshot.current_queue)
            .order_by(func.count(TicketSnapshot.ticket_id).desc())
        )
    ).all()
    return {
        "queues": [
            {"queue": r[0] or "Unknown", "count": r[1]} for r in rows
        ]
    }


@router.get("/reassignments")
async def reassignments(
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.utcnow()
    rows = (
        await db.execute(
            select(
                TicketEvent.old_owner,
                TicketEvent.new_owner,
                func.count(TicketEvent.id),
            )
            .where(
                TicketEvent.event_type == "OwnerUpdate",
                TicketEvent.new_owner.isnot(None),
                TicketEvent.old_owner.isnot(None),
                TicketEvent.new_owner != TicketEvent.old_owner,
                TicketEvent.event_time >= since,
            )
            .group_by(TicketEvent.old_owner, TicketEvent.new_owner)
            .order_by(func.count(TicketEvent.id).desc())
            .limit(50)
        )
    ).all()
    nodes = set()
    edges = []
    for r in rows:
        nodes.add(r[0])
        nodes.add(r[1])
        edges.append({"source": r[0], "target": r[1], "value": r[2]})
    return {"nodes": [{"name": n} for n in sorted(nodes)], "edges": edges}


@router.get("/approaching-breach")
async def approaching_breach(
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    q = select(SLAMetric).where(
        SLAMetric.sla_breached == False,
        SLAMetric.metric_name.in_(["response_time", "resolution_time"]),
    ).order_by(SLAMetric.metric_seconds.desc().nullslast()).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return {
        "tickets": [
            {
                "ticket_id": m.ticket_id,
                "metric_name": m.metric_name,
                "metric_seconds": m.metric_seconds,
                "queue_name": m.queue_name,
                "owner": m.owner,
                "confidence": m.confidence,
            }
            for m in rows
        ]
    }
