"""SLA Forensic Attribution API (V3) — Phase 6.

Endpoints exposed under /analytics/forensics/*. All read-only; computations
are delegated to services/forensics/ and aggregated in SQL.

Endpoints:
  GET  /analytics/forensics/queues
  GET  /analytics/forensics/owners
  GET  /analytics/forensics/transitions
  GET  /analytics/forensics/breaches
  GET  /analytics/forensics/hot-potato
  GET  /analytics/forensics/blackholes
  GET  /analytics/forensics/stagnation
  GET  /analytics/forensics/silent-breaches
  GET  /analytics/forensics/tickets/{ticket_id}/attribution
  GET  /analytics/forensics/summary
"""

import logging
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import sync_session_factory
from app.domain.models import SLADefinition, TicketSnapshot
from app.services.forensics import (
    ForensicAttributionEngine,
    InactivityEngine,
    OwnerForensicsService,
    QueueForensicsService,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------- Queue forensics -------------------------------------------------


@router.get("/queues")
def list_queue_forensics(
    limit: int = Query(100, ge=1, le=500),
    sort_by: str = Query(
        "black_hole_score",
        pattern="^(black_hole_score|parking_lot_score|routing_chaos_score|"
                "stagnation_score|breach_rate|pressure_score|total_wall_hours)$",
    ),
):
    """Per-queue forensic fingerprints."""
    with sync_session_factory() as db:
        rows = QueueForensicsService.compute_all(db, limit=limit)
    data = [asdict(r) for r in rows]
    data.sort(key=lambda d: d.get(sort_by, 0) or 0, reverse=True)
    return {"count": len(data), "queues": data}


@router.get("/blackholes")
def list_blackholes(min_score: float = Query(0.3, ge=0.0, le=1.0)):
    """Queues identified as black holes (parked + breach + low exit)."""
    with sync_session_factory() as db:
        rows = QueueForensicsService.compute_all(db, limit=200)
    out = [asdict(r) for r in rows if r.black_hole_score >= min_score]
    out.sort(key=lambda d: d["black_hole_score"], reverse=True)
    return {"threshold": min_score, "count": len(out), "queues": out}


@router.get("/stagnation")
def list_stagnation_queues():
    """Queues by stagnation score (low touch density per hour held)."""
    with sync_session_factory() as db:
        rows = QueueForensicsService.compute_all(db, limit=200)
    out = sorted(
        [asdict(r) for r in rows],
        key=lambda d: d["stagnation_score"],
        reverse=True,
    )
    return {"count": len(out), "queues": out[:50]}


# ---------- Owner forensics -------------------------------------------------


@router.get("/owners")
def list_owner_forensics(limit: int = Query(100, ge=1, le=500)):
    with sync_session_factory() as db:
        rows = OwnerForensicsService.compute_all(db, limit=limit)
        gaps = OwnerForensicsService.ownership_gaps(db, limit=50)
    return {
        "count": len(rows),
        "owners": [asdict(r) for r in rows],
        "ticket_ownership_gaps": gaps,
    }


# ---------- Transitions / routing -------------------------------------------


@router.get("/transitions")
def list_transitions(limit: int = Query(200, ge=10, le=2000)):
    with sync_session_factory() as db:
        rows = QueueForensicsService.transitions(db, limit=limit)
    return {"count": len(rows), "transitions": rows}


@router.get("/hot-potato")
def list_hot_potato(
    min_moves: int = Query(3, ge=1, le=50),
    limit: int = Query(50, ge=1, le=500),
):
    with sync_session_factory() as db:
        rows = QueueForensicsService.hot_potato_tickets(db, min_moves=min_moves, limit=limit)
    return {"count": len(rows), "tickets": rows}


# ---------- Breaches --------------------------------------------------------


@router.get("/breaches")
def list_breach_attributions(
    metric: str = Query("resolution_time", pattern="^(resolution_time|first_response_time)$"),
    limit: int = Query(100, ge=1, le=1000),
):
    """Top breached tickets with full root-cause attribution."""
    with sync_session_factory() as db:
        breached_ids = db.execute(
            text("""
                SELECT DISTINCT m.ticket_id
                FROM sla_metrics m
                WHERE m.metric_name = :mn
                  AND m.sla_breached IS TRUE
                ORDER BY m.ticket_id DESC
                LIMIT :lim
            """),
            {"mn": metric, "lim": limit},
        ).scalars().all()

        results = []
        for tid in breached_ids:
            ticket = db.query(TicketSnapshot).filter(TicketSnapshot.ticket_id == tid).first()
            if not ticket:
                continue
            sla_def = db.query(SLADefinition).filter(SLADefinition.is_active == True).first()
            if not sla_def:
                continue
            try:
                rc = ForensicAttributionEngine.compute_breach_root_cause(
                    db, ticket, sla_def, metric_name=metric,
                )
                results.append(asdict(rc))
            except Exception as exc:
                logger.exception("breach attribution failed for ticket %s: %s", tid, exc)
                continue

    return {"count": len(results), "metric": metric, "breaches": results}


@router.get("/silent-breaches")
def list_silent_breaches(
    min_ratio: float = Query(0.5, ge=0.1, le=5.0),
    limit: int = Query(200, ge=1, le=1000),
):
    """Open tickets aging silently past min_ratio × SLA target."""
    with sync_session_factory() as db:
        rows = InactivityEngine.detect_silent_breaches(db, min_inactivity_ratio=min_ratio, limit=limit)
        queue_silence = InactivityEngine.compute_queue_silence(db)
    return {
        "count": len(rows),
        "min_inactivity_ratio": min_ratio,
        "tickets": [asdict(r) for r in rows],
        "queue_silence": queue_silence,
    }


# ---------- Per-ticket attribution ------------------------------------------


@router.get("/tickets/{ticket_id}/attribution")
def ticket_attribution(
    ticket_id: int,
    metric: str = Query("resolution_time", pattern="^(resolution_time|first_response_time)$"),
):
    """Full forensic attribution for one ticket: queue blame chain + root cause."""
    with sync_session_factory() as db:
        ticket = db.query(TicketSnapshot).filter(TicketSnapshot.ticket_id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="ticket not found")
        sla_def = db.query(SLADefinition).filter(SLADefinition.is_active == True).first()
        if not sla_def:
            raise HTTPException(status_code=409, detail="no active SLA definition")

        target = (
            sla_def.response_target_seconds
            if metric == "first_response_time"
            else sla_def.resolution_target_seconds
        )
        blame_rows = ForensicAttributionEngine.compute_queue_blame(db, ticket.ticket_id, target)
        rc = ForensicAttributionEngine.compute_breach_root_cause(db, ticket, sla_def, metric_name=metric)

    return {
        "ticket_id": ticket_id,
        "metric": metric,
        "queue_blame_chain": [asdict(b) for b in blame_rows],
        "root_cause": asdict(rc),
    }


# ---------- Aggregated summary ----------------------------------------------


@router.get("/summary")
def forensic_summary():
    """Single endpoint for the Forensic Command Center dashboard.

    Returns a compact bundle of the top signals across all forensics
    services so the UI can render with one HTTP call.
    """
    with sync_session_factory() as db:
        queues = QueueForensicsService.compute_all(db, limit=50)
        owners = OwnerForensicsService.compute_all(db, limit=25)
        transitions = QueueForensicsService.transitions(db, limit=30)
        hot_potato = QueueForensicsService.hot_potato_tickets(db, min_moves=3, limit=20)
        silent = InactivityEngine.detect_silent_breaches(db, min_inactivity_ratio=0.5, limit=20)
        queue_silence = InactivityEngine.compute_queue_silence(db)

        # Aggregate KPIs from sla_metrics
        kpis = db.execute(
            text("""
                SELECT
                  SUM(CASE WHEN metric_name='pause_seconds'        THEN metric_seconds ELSE 0 END) AS pause_total,
                  SUM(CASE WHEN metric_name='idle_seconds'         THEN metric_seconds ELSE 0 END) AS idle_total,
                  SUM(CASE WHEN metric_name='no_owner_seconds'     THEN metric_seconds ELSE 0 END) AS no_owner_total,
                  SUM(CASE WHEN metric_name='ownership_gap_seconds' THEN metric_seconds ELSE 0 END) AS gap_total,
                  SUM(CASE WHEN metric_name='transfer_wait_seconds' THEN metric_seconds ELSE 0 END) AS xfer_total,
                  SUM(CASE WHEN metric_name='stagnation_seconds'   THEN metric_seconds ELSE 0 END) AS stag_total,
                  SUM(CASE WHEN metric_name='wall_resolution_time' THEN metric_seconds ELSE 0 END) AS wall_total,
                  COUNT(*) FILTER (
                    WHERE metric_name='wall_resolution_time' AND sla_breached IS TRUE
                  ) AS wall_breached,
                  COUNT(*) FILTER (
                    WHERE metric_name='resolution_time' AND sla_breached IS TRUE
                  ) AS active_breached
                FROM sla_metrics
            """),
        ).mappings().first() or {}

    return {
        "kpis": {k: int(v or 0) for k, v in dict(kpis).items()},
        "queues_top_blackholes": sorted(
            [asdict(q) for q in queues],
            key=lambda d: d["black_hole_score"], reverse=True,
        )[:10],
        # Use raw entropy_bits — high raw entropy = wide dispersion in absolute
        # terms (e.g. ServiceDesk fanning to 36 queues). routing_chaos_score
        # is the normalized companion (0..1) for small-queue comparison.
        "queues_top_chaos": sorted(
            [asdict(q) for q in queues],
            key=lambda d: (d["entropy_bits"], d["unique_targets"]),
            reverse=True,
        )[:10],
        "queues_top_breach": sorted(
            [asdict(q) for q in queues],
            key=lambda d: d["breach_rate"], reverse=True,
        )[:10],
        "owners_top_load": [asdict(o) for o in owners[:10]],
        "owners_idle": [asdict(o) for o in owners if o.idle_flag][:20],
        "transitions": transitions,
        "hot_potato": hot_potato,
        "silent_breaches": [asdict(s) for s in silent],
        "queue_silence": queue_silence[:20],
    }
