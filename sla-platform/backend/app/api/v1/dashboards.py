from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, select, func, text, Integer
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
from app.services.analytics.advanced_analytics import AdvancedAnalytics
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get("/overview", response_model=dict)
async def dashboard_overview(
    days: int = Query(30, ge=1, le=365),
    queue: list[str] = Query(default=[],
        description="One or more queue names to scope all KPIs to (e.g. favorite queues)."),
    db: AsyncSession = Depends(get_db),
):
    # Support multi-value ?queue=A&queue=B&queue=C from URL (List/Sidebar).
    return await DashboardService.get_overview(db, days=days, queues=queue or None)


@router.get("/time-series", response_model=dict)
async def time_series(
    metric: str = Query("tickets_created"),
    granularity: str = Query("daily"),
    days: int = Query(30, ge=1, le=365),
    queue: list[str] = Query(default=[]),
    db: AsyncSession = Depends(get_db),
):
    data = await DashboardService.get_time_series(
        db, metric, granularity, days, queues=queue or None,
    )
    return {"metric": metric, "granularity": granularity, "data": data}


@router.get("/teams", response_model=dict)
async def teams_analytics(
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    return {"teams": await DashboardService.get_teams_analytics(db, days=days)}


@router.get("/ticket-flow", response_model=dict)
async def ticket_flow(
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    return await DashboardService.get_ticket_flow(db, days=days)


@router.get("/sla-trend", response_model=dict)
async def sla_trend(
    days: int = Query(30, ge=1, le=365),
    queue: list[str] = Query(default=[]),
    db: AsyncSession = Depends(get_db),
):
    """Daily SLA breach trend over the requested window.

    Previously this endpoint anchored ``since`` at today's midnight and
    ignored ``days`` — yielding at most one data point and an empty
    dashboard chart. We now honor ``days`` so the trend actually trends.
    """
    from datetime import timedelta
    since = datetime.utcnow() - timedelta(days=days)
    q = (
        select(
            func.date_trunc("day", SLAMetric.computed_at).label("day"),
            func.count(SLAMetric.id),
            func.sum(case((SLAMetric.sla_breached == True, 1), else_=0)).label("breached"),
        )
        .where(SLAMetric.computed_at >= since)
    )
    if queue:
        q = q.where(SLAMetric.queue_name.in_(queue))
    q = q.group_by(text("day")).order_by(text("day"))
    rows = (await db.execute(q)).all()
    return {
        "trend": [
            {"date": str(r[0].date()), "total": r[1] or 0, "breached": int(r[2] or 0)}
            for r in rows
        ]
    }


@router.get("/by-queue", response_model=dict)
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


@router.get("/reassignments", response_model=dict)
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


@router.get("/approaching-breach", response_model=dict)
async def approaching_breach(
    limit: int = Query(20, le=100),
    queue: list[str] = Query(default=[]),
    db: AsyncSession = Depends(get_db),
):
    # V2 engine emits "first_response_time"; the legacy "response_time"
    # name was never produced, so old filter returned nothing.
    q = select(SLAMetric).where(
        SLAMetric.sla_breached == False,
        SLAMetric.metric_name.in_(["first_response_time", "resolution_time"]),
    )
    if queue:
        q = q.where(SLAMetric.queue_name.in_(queue))
    q = q.order_by(SLAMetric.metric_seconds.desc().nullslast()).limit(limit)
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


# ── Phase 5D: Advanced Analytics Endpoints ──


@router.get("/analytics/sla-forecast", response_model=dict)
async def analytics_sla_forecast(
    days: int = Query(90, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
):
    return await AdvancedAnalytics.sla_trend_forecast(db, days=days)


@router.get("/analytics/queue-overload", response_model=dict)
async def analytics_queue_overload(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    return {"queues": await AdvancedAnalytics.queue_overload_prediction(db, days=days)}


@router.get("/analytics/reassignments", response_model=dict)
async def analytics_reassignments(
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    return await AdvancedAnalytics.reassignment_analysis(db, days=days)


@router.get("/analytics/agent-workload", response_model=dict)
async def analytics_agent_workload(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    return {"agents": await AdvancedAnalytics.agent_workload(db, days=days)}


@router.get("/analytics/problematic-queues", response_model=dict)
async def analytics_problematic_queues(
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    return {"queues": await AdvancedAnalytics.top_problematic_queues(db, days=days)}


@router.get("/analytics/mttr-mtta", response_model=dict)
async def analytics_mttr_mtta(
    days: int = Query(90, ge=1, le=365),
    queue: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await AdvancedAnalytics.mttr_mtta(db, days=days, by_queue=queue)


@router.get("/analytics/aging-tickets", response_model=dict)
async def analytics_aging_tickets(
    db: AsyncSession = Depends(get_db),
):
    return await AdvancedAnalytics.aging_tickets(db)


@router.get("/analytics/ftr-rate", response_model=dict)
async def analytics_ftr_rate(
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    return await AdvancedAnalytics.first_touch_resolution(db, days=days)


@router.get("/analytics/reopen-rate", response_model=dict)
async def analytics_reopen_rate(
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    return await AdvancedAnalytics.reopen_rate(db, days=days)


@router.get("/analytics/breach-root-cause", response_model=dict)
async def analytics_breach_root_cause(
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    return await AdvancedAnalytics.breach_root_cause(db, days=days)
