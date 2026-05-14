from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domain.models import (
    OwnershipPeriod,
    QueuePeriod,
    SLAMetric,
    TicketEvent,
    TicketSnapshot,
)

router = APIRouter()


@router.get("")
async def list_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    queue: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    confidence: Optional[str] = Query(None),
    is_closed: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(TicketSnapshot)
    count_q = select(func.count(TicketSnapshot.ticket_id))

    if queue:
        q = q.where(TicketSnapshot.current_queue.ilike(f"%{queue}%"))
        count_q = count_q.where(TicketSnapshot.current_queue.ilike(f"%{queue}%"))
    if state:
        q = q.where(TicketSnapshot.current_state == state)
        count_q = count_q.where(TicketSnapshot.current_state == state)
    if confidence:
        q = q.where(TicketSnapshot.confidence == confidence)
        count_q = count_q.where(TicketSnapshot.confidence == confidence)
    if is_closed is not None:
        q = q.where(TicketSnapshot.is_closed == is_closed)
        count_q = count_q.where(TicketSnapshot.is_closed == is_closed)
    if search:
        pattern = f"%{search}%"
        q = q.where(
            TicketSnapshot.ticket_number.ilike(pattern)
            | TicketSnapshot.title.ilike(pattern)
        )
        count_q = count_q.where(
            TicketSnapshot.ticket_number.ilike(pattern)
            | TicketSnapshot.title.ilike(pattern)
        )

    total = (await db.execute(count_q)).scalar() or 0
    offset = (page - 1) * page_size
    q = q.order_by(desc(TicketSnapshot.updated_at_ts)).offset(offset).limit(page_size)
    tickets = (await db.execute(q)).scalars().all()

    return {
        "tickets": [
            {
                "ticket_id": t.ticket_id,
                "ticket_number": t.ticket_number,
                "title": t.title,
                "current_queue": t.current_queue,
                "current_state": t.current_state,
                "current_owner": t.current_owner,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
                "first_response_at": t.first_response_at.isoformat() if t.first_response_at else None,
                "resolution_at": t.resolution_at.isoformat() if t.resolution_at else None,
                "is_closed": t.is_closed,
                "confidence": t.confidence,
            }
            for t in tickets
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{ticket_id}")
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
):
    t = await db.get(TicketSnapshot, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return {
        "ticket_id": t.ticket_id,
        "ticket_number": t.ticket_number,
        "title": t.title,
        "customer_id": t.customer_id,
        "customer_user_id": t.customer_user_id,
        "current_queue": t.current_queue,
        "current_state": t.current_state,
        "current_owner": t.current_owner,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        "first_response_at": t.first_response_at.isoformat() if t.first_response_at else None,
        "resolution_at": t.resolution_at.isoformat() if t.resolution_at else None,
        "is_closed": t.is_closed,
        "is_merged": t.is_merged,
        "confidence": t.confidence,
        "last_import_id": str(t.last_import_id) if t.last_import_id else None,
    }


@router.get("/{ticket_id}/timeline")
async def get_ticket_timeline(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
):
    events = (
        await db.execute(
            select(TicketEvent)
            .where(TicketEvent.ticket_id == ticket_id)
            .order_by(TicketEvent.event_seq)
        )
    ).scalars().all()

    return {
        "events": [
            {
                "id": e.id,
                "event_seq": e.event_seq,
                "event_time": e.event_time.isoformat() if e.event_time else None,
                "event_type": e.event_type,
                "queue_name": e.queue_name,
                "state_name": e.state_name,
                "owner_name": e.owner_name,
                "src_queue": e.src_queue,
                "dest_queue": e.dest_queue,
                "old_state": e.old_state,
                "new_state": e.new_state,
                "new_owner": e.new_owner,
                "old_owner": e.old_owner,
                "pending_until": e.pending_until.isoformat() if e.pending_until else None,
                "is_system_action": e.is_system_action,
            }
            for e in events
        ]
    }


@router.get("/{ticket_id}/ownership")
async def get_ticket_ownership(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
):
    periods = (
        await db.execute(
            select(OwnershipPeriod)
            .where(OwnershipPeriod.ticket_id == ticket_id)
            .order_by(OwnershipPeriod.start_time)
        )
    ).scalars().all()
    return {
        "ownership_periods": [
            {
                "id": p.id,
                "owner": p.owner,
                "queue_name": p.queue_name,
                "team_prefix": p.team_prefix,
                "start_time": p.start_time.isoformat() if p.start_time else None,
                "end_time": p.end_time.isoformat() if p.end_time else None,
                "duration_seconds": p.duration_seconds,
                "is_active": p.is_active,
            }
            for p in periods
        ]
    }


@router.get("/{ticket_id}/queue-periods")
async def get_ticket_queue_periods(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
):
    periods = (
        await db.execute(
            select(QueuePeriod)
            .where(QueuePeriod.ticket_id == ticket_id)
            .order_by(QueuePeriod.entered_at)
        )
    ).scalars().all()
    return {
        "queue_periods": [
            {
                "id": p.id,
                "queue_name": p.queue_name,
                "team_prefix": p.team_prefix,
                "entered_at": p.entered_at.isoformat() if p.entered_at else None,
                "exited_at": p.exited_at.isoformat() if p.exited_at else None,
                "duration_seconds": p.duration_seconds,
                "owner_count": p.owner_count,
            }
            for p in periods
        ]
    }


@router.get("/{ticket_id}/sla")
async def get_ticket_sla(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
):
    metrics = (
        await db.execute(
            select(SLAMetric)
            .where(SLAMetric.ticket_id == ticket_id)
            .order_by(SLAMetric.metric_name)
        )
    ).scalars().all()
    return {
        "sla_metrics": [
            {
                "id": m.id,
                "metric_name": m.metric_name,
                "metric_seconds": m.metric_seconds,
                "sla_breached": m.sla_breached,
                "queue_name": m.queue_name,
                "owner": m.owner,
                "team_prefix": m.team_prefix,
                "sla_definition_id": m.sla_definition_id,
                "confidence": m.confidence,
                "computed_at": m.computed_at.isoformat() if m.computed_at else None,
            }
            for m in metrics
        ]
    }
