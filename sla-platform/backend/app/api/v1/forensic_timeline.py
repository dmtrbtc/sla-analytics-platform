"""Forensic timeline endpoint — v1.7."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.database import sync_session_factory
from app.core.dependencies import get_current_user
from app.services.forensics.timeline_engine import TimelineEngine

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/{ticket_id}")
def ticket_timeline(
    ticket_id: int,
    response_target_seconds: int = Query(1800, ge=60, le=86400 * 7),
    resolution_target_seconds: int = Query(28800, ge=60, le=86400 * 30),
):
    """Full forensic queue timeline + response/resolution loss per queue."""
    with sync_session_factory() as db:
        result = TimelineEngine.for_ticket(
            db, ticket_id,
            response_target_seconds=response_target_seconds,
            resolution_target_seconds=resolution_target_seconds,
        )
        if result.get("error"):
            raise HTTPException(404, result["error"])
        return result
