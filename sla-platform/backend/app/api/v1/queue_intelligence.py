"""OTRS Queue Intelligence API — real-data-driven SLA forensics.

Endpoints for the OTRS SLA Operations Intelligence Platform.
All analytics driven by real user data, not generic models.
"""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import sync_session_factory
from app.core.dependencies import get_current_user
from app.services.queue_intelligence import QueueIntelligenceEngine

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/queue-flow-map")
def get_queue_flow_map(
    days: int = Query(30, ge=1, le=365),
):
    """Queue flow map — who transfers to whom with breach and delay data."""
    with sync_session_factory() as db:
        result = QueueIntelligenceEngine.get_queue_flow_map(db, days=days)
    return result


@router.get("/queue-forensics")
def get_queue_forensics(
    days: int = Query(30, ge=1, le=365),
):
    """Deep queue forensic analysis — per-queue SLA death location."""
    with sync_session_factory() as db:
        result = QueueIntelligenceEngine.get_queue_forensics(db, days=days)
    return result


@router.get("/transfer-analytics")
def get_transfer_analytics(
    days: int = Query(30, ge=1, le=365),
):
    """Transfer storms, loops, routing inefficiency analysis."""
    with sync_session_factory() as db:
        result = QueueIntelligenceEngine.get_transfer_analytics(db, days=days)
    return result


@router.get("/servicedesk-intelligence")
def get_servicedesk_intelligence(
    days: int = Query(30, ge=1, le=365),
):
    """ServiceDesk analytics — intake, transfer quality, downstream damage."""
    with sync_session_factory() as db:
        result = QueueIntelligenceEngine.get_servicedesk_intelligence(db, days=days)
    return result


@router.get("/ticket-forensic/{ticket_id}")
def get_ticket_forensic(ticket_id: int):
    """Full forensic timeline for a single ticket — queue-by-queue SLA analysis."""
    with sync_session_factory() as db:
        result = QueueIntelligenceEngine.get_ticket_lifecycle_forensic(db, ticket_id)
    return result


@router.get("/ticket-root-cause/{ticket_id}")
def get_ticket_root_cause(ticket_id: int):
    """AI-style root cause explanation in Russian."""
    with sync_session_factory() as db:
        result = QueueIntelligenceEngine.generate_root_cause(db, ticket_id)
    return {"root_cause": result}


@router.get("/overview")
def get_intelligence_overview(
    days: int = Query(30, ge=1, le=365),
):
    """Combined intelligence overview for the OTRS Command Center."""
    with sync_session_factory() as db:
        forensics = QueueIntelligenceEngine.get_queue_forensics(db, days=days)
        flow_map = QueueIntelligenceEngine.get_queue_flow_map(db, days=days)
        sd = QueueIntelligenceEngine.get_servicedesk_intelligence(db, days=days)
        transfers = QueueIntelligenceEngine.get_transfer_analytics(db, days=days)

    total_queues = len(forensics.get("queues", []))
    total_breaches = sum(q["breaches"] for q in forensics.get("queues", []))
    total_tickets = sum(q["total_tickets"] for q in forensics.get("queues", []))
    degraded_queues = len(forensics.get("systemically_degraded", []))
    needs_sla_revision = len(forensics.get("queues_needing_sla_revision", []))
    degraded_flows = len(flow_map.get("degraded_flows", []))
    sd_downstream = len(sd.get("downstream", []))
    high_transfer = len(transfers.get("high_transfer_tickets", []))

    return {
        "summary": {
            "total_queues": total_queues,
            "total_breaches": total_breaches,
            "total_tickets": total_tickets,
            "degraded_queues": degraded_queues,
            "queues_needing_sla_revision": needs_sla_revision,
            "degraded_flows": degraded_flows,
            "servicedesk_downstream_queues": sd_downstream,
            "high_transfer_tickets": high_transfer,
            "avg_breach_pct": forensics.get("avg_breach_pct", 0),
        },
        "top_degraded_queues": forensics.get("systemically_degraded", [])[:10],
        "servicedesk": {
            "downstream": sd.get("downstream", [])[:10],
            "total_intake": sd.get("total_sd_intake", 0),
        },
        "top_transfer_loops": transfers.get("transfer_loops", [])[:5],
        "top_bounce_queues": transfers.get("bounce_queues", [])[:5],
    }
