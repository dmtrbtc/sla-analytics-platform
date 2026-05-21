"""SLA-loss aggregate API — v1.8.

Endpoints:
  GET /analytics/sla-loss/top-queues
  GET /analytics/sla-loss/most-expensive
  GET /analytics/sla-loss/dying-in-queue
  GET /analytics/sla-loss/parking-lots
  GET /analytics/sla-loss/waterfall/{ticket_id}
  GET /analytics/sla-loss/overview          ← bundled for the "Where SLA dies" page
"""
import logging
from fastapi import APIRouter, Depends, Query

from app.core.database import sync_session_factory
from app.core.dependencies import get_current_user
from app.services.forensics.sla_loss_engine import SLALossEngine

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/top-queues")
def top_loss_queues(
    limit: int = Query(25, ge=1, le=200),
    days: int | None = Query(None, ge=1, le=365),
    queue: list[str] = Query(default=[]),
):
    with sync_session_factory() as db:
        return {"queues": SLALossEngine.top_loss_queues(db, limit=limit, queues=queue or None, days=days)}


@router.get("/most-expensive")
def most_expensive_queues(
    limit: int = Query(25, ge=1, le=200),
    min_tickets: int = Query(5, ge=1, le=1000),
    queue: list[str] = Query(default=[]),
):
    with sync_session_factory() as db:
        return {"queues": SLALossEngine.most_expensive_queues(
            db, limit=limit, queues=queue or None, min_tickets=min_tickets,
        )}


@router.get("/dying-in-queue")
def dying_in_queue(
    limit: int = Query(25, ge=1, le=200),
    queue: list[str] = Query(default=[]),
):
    with sync_session_factory() as db:
        return {"tickets": SLALossEngine.dying_in_queue(db, limit=limit, queues=queue or None)}


@router.get("/parking-lots")
def parking_lots(
    limit: int = Query(25, ge=1, le=200),
    queue: list[str] = Query(default=[]),
):
    with sync_session_factory() as db:
        return {"queues": SLALossEngine.parking_lots(db, limit=limit, queues=queue or None)}


@router.get("/waterfall/{ticket_id}")
def waterfall(ticket_id: int):
    with sync_session_factory() as db:
        return {"ticket_id": ticket_id, "segments": SLALossEngine.waterfall(db, ticket_id)}


@router.get("/overview")
def loss_overview(queue: list[str] = Query(default=[])):
    q = queue or None
    with sync_session_factory() as db:
        return {
            "top_loss_queues": SLALossEngine.top_loss_queues(db, limit=15, queues=q),
            "most_expensive": SLALossEngine.most_expensive_queues(db, limit=15, queues=q),
            "dying_in_queue": SLALossEngine.dying_in_queue(db, limit=15, queues=q),
            "parking_lots": SLALossEngine.parking_lots(db, limit=15, queues=q),
        }
