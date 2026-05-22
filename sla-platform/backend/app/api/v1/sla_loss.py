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
from app.services.forensics.time_scope import parse_time_scope

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


# ----- shared scope query params -------------------------------------------
# Standard four params on every analytics endpoint. parse_time_scope handles
# precedence (period > since/until > all-time) and malformed input.
def _scope(period: str | None, since: str | None, until: str | None):
    return parse_time_scope(period=period, since=since, until=until)


@router.get("/top-queues")
def top_loss_queues(
    limit: int = Query(25, ge=1, le=200),
    days: int | None = Query(None, ge=1, le=365),
    queue: list[str] = Query(default=[]),
    period: str | None = Query(None, description="24h | 7d | 30d | 90d | …"),
    since: str | None = Query(None),
    until: str | None = Query(None),
):
    scope = _scope(period, since, until)
    with sync_session_factory() as db:
        return {
            "scope": scope.to_dict(),
            "queues": SLALossEngine.top_loss_queues(
                db, limit=limit, queues=queue or None, days=days, scope=scope,
            ),
        }


@router.get("/most-expensive")
def most_expensive_queues(
    limit: int = Query(25, ge=1, le=200),
    min_tickets: int = Query(5, ge=1, le=1000),
    queue: list[str] = Query(default=[]),
    period: str | None = Query(None),
    since: str | None = Query(None),
    until: str | None = Query(None),
):
    scope = _scope(period, since, until)
    with sync_session_factory() as db:
        return {
            "scope": scope.to_dict(),
            "queues": SLALossEngine.most_expensive_queues(
                db, limit=limit, queues=queue or None,
                min_tickets=min_tickets, scope=scope,
            ),
        }


@router.get("/dying-in-queue")
def dying_in_queue(
    limit: int = Query(25, ge=1, le=200),
    queue: list[str] = Query(default=[]),
    period: str | None = Query(None),
    since: str | None = Query(None),
    until: str | None = Query(None),
):
    scope = _scope(period, since, until)
    with sync_session_factory() as db:
        return {
            "scope": scope.to_dict(),
            "tickets": SLALossEngine.dying_in_queue(
                db, limit=limit, queues=queue or None, scope=scope,
            ),
        }


@router.get("/parking-lots")
def parking_lots(
    limit: int = Query(25, ge=1, le=200),
    queue: list[str] = Query(default=[]),
    period: str | None = Query(None),
    since: str | None = Query(None),
    until: str | None = Query(None),
):
    scope = _scope(period, since, until)
    with sync_session_factory() as db:
        return {
            "scope": scope.to_dict(),
            "queues": SLALossEngine.parking_lots(
                db, limit=limit, queues=queue or None, scope=scope,
            ),
        }


@router.get("/waterfall/{ticket_id}")
def waterfall(ticket_id: int):
    with sync_session_factory() as db:
        return {"ticket_id": ticket_id, "segments": SLALossEngine.waterfall(db, ticket_id)}


@router.get("/overview")
def loss_overview(
    queue: list[str] = Query(default=[]),
    period: str | None = Query(None),
    since: str | None = Query(None),
    until: str | None = Query(None),
):
    q = queue or None
    scope = _scope(period, since, until)
    with sync_session_factory() as db:
        return {
            "scope": scope.to_dict(),
            "top_loss_queues": SLALossEngine.top_loss_queues(db, limit=15, queues=q, scope=scope),
            "most_expensive": SLALossEngine.most_expensive_queues(db, limit=15, queues=q, scope=scope),
            "dying_in_queue": SLALossEngine.dying_in_queue(db, limit=15, queues=q, scope=scope),
            "parking_lots": SLALossEngine.parking_lots(db, limit=15, queues=q, scope=scope),
        }
