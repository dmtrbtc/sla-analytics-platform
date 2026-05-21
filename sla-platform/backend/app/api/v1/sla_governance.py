"""SLA Governance & Operations — v1.5 additions.

Endpoints:

  Forensic contribution:
    GET  /analytics/forensics/tickets/{ticket_id}/contribution

  SLA rule governance:
    GET  /sla/queue-rules/{rule_id}/matched-tickets
    GET  /sla/queue-rules/conflicts
    POST /sla/simulate

  Team operations dashboard:
    GET  /teams/{team_id}/dashboard
"""
from __future__ import annotations

import fnmatch
import logging
from dataclasses import asdict
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import sync_session_factory
from app.core.dependencies import get_current_user
from app.domain.models import SLAQueueRule, Team, User
from app.services.forensics.contribution_engine import ContributionEngine

logger = logging.getLogger(__name__)


# ─── 1.  Forensic contribution router  ──────────────────────────────────────
contribution_router = APIRouter(dependencies=[Depends(get_current_user)])


@contribution_router.get("/tickets/{ticket_id}/contribution")
def ticket_contribution(ticket_id: int):
    """Per-ticket queue + owner contribution breakdown with the v1.5
    operational waste / routing / stagnation / transfer / touch scores."""
    with sync_session_factory() as db:
        # Verify ticket exists; otherwise the engine still returns zeros
        exists = db.execute(
            text("SELECT 1 FROM ticket_snapshots WHERE ticket_id = :tid"),
            {"tid": ticket_id},
        ).scalar()
        if not exists:
            raise HTTPException(404, "Ticket not found in current snapshots")
        c = ContributionEngine.for_ticket(db, ticket_id)
    return {
        "ticket_id": c.ticket_id,
        "total_wall_seconds": c.total_wall_seconds,
        "queue_contributions": [asdict(q) for q in c.queue_contributions],
        "owner_contributions": [asdict(o) for o in c.owner_contributions],
        "scores": {
            "routing_instability_score": c.routing_instability_score,
            "stagnation_score": c.stagnation_score,
            "operational_waste_score": c.operational_waste_score,
            "transfer_efficiency": c.transfer_efficiency,
            "touch_efficiency": c.touch_efficiency,
        },
    }


# ─── 2.  SLA rule governance router  ────────────────────────────────────────
sla_governance_router = APIRouter(dependencies=[Depends(get_current_user)])


@sla_governance_router.get("/queue-rules/{rule_id}/matched-tickets")
def rule_matched_tickets(rule_id: UUID, limit: int = Query(50, ge=1, le=500)):
    """Show real tickets whose `current_queue` matches this rule's pattern.

    Powers the "what would this rule affect?" preview in the SLA Config UI.
    """
    with sync_session_factory() as db:
        rule = db.get(SLAQueueRule, rule_id)
        if not rule:
            raise HTTPException(404, "Rule not found")
        # Use Postgres LIKE with glob-to-LIKE translation for SQL-side match.
        # Convert `*` → `%`, `?` → `_`, escape `%` and `_`.
        like = (
            (rule.queue_pattern or "")
            .replace("%", r"\%").replace("_", r"\_")
            .replace("*", "%").replace("?", "_")
        )
        rows = db.execute(
            text("""
                SELECT ticket_id, ticket_number, title, current_queue,
                       current_state, current_owner, is_closed
                FROM ticket_snapshots
                WHERE current_queue LIKE :pat
                ORDER BY ticket_id DESC
                LIMIT :lim
            """),
            {"pat": like, "lim": limit},
        ).mappings().all()
        total = db.execute(
            text("SELECT COUNT(*) FROM ticket_snapshots WHERE current_queue LIKE :pat"),
            {"pat": like},
        ).scalar() or 0
        # Aggregate by queue for the impact preview
        per_q = db.execute(
            text("""
                SELECT current_queue AS queue, COUNT(*) AS n,
                       SUM(CASE WHEN is_closed THEN 0 ELSE 1 END) AS open_n
                FROM ticket_snapshots
                WHERE current_queue LIKE :pat
                GROUP BY current_queue
                ORDER BY n DESC
            """),
            {"pat": like},
        ).mappings().all()
    return {
        "rule_id": str(rule_id),
        "queue_pattern": rule.queue_pattern,
        "like_translation": like,
        "matched_total": int(total),
        "by_queue": [dict(r) for r in per_q],
        "sample_tickets": [dict(r) for r in rows],
    }


@sla_governance_router.get("/queue-rules/conflicts")
def rule_conflicts():
    """Detect overlapping queue patterns + impossible-target rules.

    Two rules conflict when:
      - Any concrete queue_name (from ticket_snapshots) matches both
        patterns and the two rules have different response targets.
      - The lower-priority rule will be shadowed for tickets in that queue.

    Impossible-target rules: `resolution_target_seconds <= 0` or
    `response_target_seconds > resolution_target_seconds`.
    """
    with sync_session_factory() as db:
        rules = list(db.execute(
            text("""
                SELECT id, name, queue_pattern, priority,
                       response_target_seconds, resolution_target_seconds,
                       is_active
                FROM sla_queue_rules
                WHERE is_active = true
                ORDER BY priority DESC NULLS LAST, created_at ASC
            """),
        ).mappings().all())
        queues = [r[0] for r in db.execute(
            text("""
                SELECT DISTINCT current_queue FROM ticket_snapshots
                WHERE current_queue IS NOT NULL
            """),
        ).all()]

    # Match each queue to all matching rules; flag conflicts.
    overlap: list[dict[str, Any]] = []
    queue_to_rules: dict[str, list[dict]] = {}
    for q in queues:
        matches = [r for r in rules if fnmatch.fnmatch(q, r["queue_pattern"] or "")]
        if len(matches) >= 2:
            queue_to_rules[q] = [dict(m) for m in matches]
            # If any two have different response or resolution targets, conflict
            distinct_resp = {m["response_target_seconds"] for m in matches}
            distinct_resol = {m["resolution_target_seconds"] for m in matches}
            if len(distinct_resp) > 1 or len(distinct_resol) > 1:
                overlap.append({
                    "queue": q,
                    "rules": [
                        {
                            "id": str(m["id"]), "name": m["name"],
                            "priority": m["priority"], "pattern": m["queue_pattern"],
                            "response": m["response_target_seconds"],
                            "resolution": m["resolution_target_seconds"],
                        }
                        for m in matches
                    ],
                })

    impossible = [
        {
            "id": str(r["id"]), "name": r["name"], "pattern": r["queue_pattern"],
            "reason": (
                "resolution_target_seconds <= 0"
                if (r["resolution_target_seconds"] or 0) <= 0
                else "response_target > resolution_target"
            ),
        }
        for r in rules
        if (r["resolution_target_seconds"] or 0) <= 0
        or (r["response_target_seconds"] or 0) > (r["resolution_target_seconds"] or 0)
    ]

    # Rules that match zero real queues — "dead rules"
    dead = []
    for r in rules:
        if not any(fnmatch.fnmatch(q, r["queue_pattern"] or "") for q in queues):
            dead.append({
                "id": str(r["id"]), "name": r["name"], "pattern": r["queue_pattern"],
            })

    return {
        "rule_count": len(rules),
        "queue_count": len(queues),
        "overlap_conflicts": overlap,
        "impossible_rules": impossible,
        "dead_rules": dead,
        "queue_rule_map": queue_to_rules,
    }


class _SimulatePayload(BaseModel):
    ticket_id: int
    queue_pattern: str
    response_target_seconds: int
    resolution_target_seconds: int


@sla_governance_router.post("/simulate")
def simulate_rule(payload: _SimulatePayload):
    """Replay a single ticket against a proposed rule. Returns what the
    breach decision would have been WITHOUT mutating any data."""
    with sync_session_factory() as db:
        ticket = db.execute(
            text("""
                SELECT ticket_id, ticket_number, current_queue, current_state,
                       created_at, first_response_at, resolution_at,
                       updated_at, is_closed
                FROM ticket_snapshots WHERE ticket_id = :tid
            """),
            {"tid": payload.ticket_id},
        ).mappings().first()
        if not ticket:
            raise HTTPException(404, "Ticket not found")
        matched = fnmatch.fnmatch(ticket["current_queue"] or "", payload.queue_pattern)
        from datetime import datetime, timezone
        end = ticket["resolution_at"] or ticket["updated_at"] or datetime.now(timezone.utc)
        first_resp = ticket["first_response_at"]
        wall_resp = int((first_resp - ticket["created_at"]).total_seconds()) if (first_resp and ticket["created_at"]) else None
        wall_resol = int((end - ticket["created_at"]).total_seconds()) if ticket["created_at"] else None
        # Existing computed metrics (V2 active-time) for comparison
        existing = db.execute(
            text("""
                SELECT metric_name, metric_seconds, sla_breached
                FROM sla_metrics
                WHERE ticket_id = :tid
                  AND metric_name IN ('first_response_time','resolution_time',
                                      'wall_response_time','wall_resolution_time')
            """),
            {"tid": payload.ticket_id},
        ).mappings().all()
    return {
        "ticket_id": payload.ticket_id,
        "ticket_number": ticket["ticket_number"],
        "current_queue": ticket["current_queue"],
        "rule_pattern": payload.queue_pattern,
        "rule_matches_ticket": matched,
        "simulation": {
            "wall_response_seconds": wall_resp,
            "wall_resolution_seconds": wall_resol,
            "response_target_seconds": payload.response_target_seconds,
            "resolution_target_seconds": payload.resolution_target_seconds,
            "wall_response_breach":
                wall_resp is not None and wall_resp > payload.response_target_seconds,
            "wall_resolution_breach":
                wall_resol is not None and wall_resol > payload.resolution_target_seconds,
        },
        "existing_metrics": [dict(r) for r in existing],
    }


# ─── 3.  Team operational dashboard router  ─────────────────────────────────
team_dash_router = APIRouter(dependencies=[Depends(get_current_user)])


@team_dash_router.get("/{team_id}/dashboard")
def team_dashboard(team_id: int, days: int = Query(30, ge=1, le=365)):
    """MTTR / MTTA / breach / no-owner / reassignment metrics for a team.

    Team scope = queues stored in `teams.queues` JSONB, plus all queues
    starting with `teams.queue_prefix`.
    """
    with sync_session_factory() as db:
        team = db.get(Team, team_id)
        if not team:
            raise HTTPException(404, "Team not found")
        queues_extra = team.queues or []
        prefix = team.queue_prefix or ""

        # Get all queue names matching prefix
        prefix_rows = db.execute(
            text("""
                SELECT DISTINCT current_queue FROM ticket_snapshots
                WHERE current_queue LIKE :px ESCAPE '\\'
            """),
            {"px": prefix.replace("%", r"\%").replace("_", r"\_") + "%"},
        ).scalars().all()
        scope = list({*queues_extra, *prefix_rows})
        if not scope:
            return {
                "team": {"id": team.id, "name": team.name, "queue_prefix": prefix},
                "scope_queues": [],
                "message": "No queues match this team",
            }

        # Tickets in scope
        total = db.execute(
            text("""
                SELECT COUNT(*) FROM ticket_snapshots
                WHERE current_queue = ANY(:scope)
            """),
            {"scope": scope},
        ).scalar() or 0
        open_n = db.execute(
            text("""
                SELECT COUNT(*) FROM ticket_snapshots
                WHERE current_queue = ANY(:scope) AND is_closed = false
            """),
            {"scope": scope},
        ).scalar() or 0

        # MTTA / MTTR / breach
        metrics = db.execute(
            text("""
                SELECT metric_name,
                       COUNT(*) AS n,
                       AVG(metric_seconds)::bigint AS avg_sec,
                       SUM(CASE WHEN sla_breached THEN 1 ELSE 0 END) AS breaches
                FROM sla_metrics
                WHERE queue_name = ANY(:scope)
                GROUP BY metric_name
            """),
            {"scope": scope},
        ).mappings().all()
        m: dict[str, dict] = {}
        for r in metrics:
            m[r["metric_name"]] = {
                "n": int(r["n"]), "avg": int(r["avg_sec"] or 0),
                "breaches": int(r["breaches"] or 0),
            }

        # No-owner share
        no_own = db.execute(
            text("""
                SELECT
                  SUM(EXTRACT(EPOCH FROM
                       (COALESCE(end_time, NOW()) - start_time)))::bigint AS owned_total,
                  SUM(CASE WHEN owner IS NULL OR LOWER(owner) IN
                       ('root@localhost','otrs admin (root@localhost)','')
                       THEN EXTRACT(EPOCH FROM
                            (COALESCE(end_time, NOW()) - start_time))
                       ELSE 0 END)::bigint AS no_owner_total
                FROM ownership_periods
                WHERE queue_name = ANY(:scope)
            """),
            {"scope": scope},
        ).mappings().first() or {}

        # Reassignment storms in scope
        reassigns = db.execute(
            text("""
                SELECT COUNT(*) FROM ticket_events
                WHERE queue_name = ANY(:scope)
                  AND new_owner IS NOT NULL AND old_owner IS NOT NULL
                  AND new_owner != old_owner
            """),
            {"scope": scope},
        ).scalar() or 0

        # Bounce rate
        bounces = db.execute(
            text("""
                SELECT COUNT(*) FROM ticket_events
                WHERE src_queue = ANY(:scope)
                  AND dest_queue IS NOT NULL AND src_queue != dest_queue
            """),
            {"scope": scope},
        ).scalar() or 0

        # Top overloaded owners
        top_owners = db.execute(
            text("""
                SELECT owner, COUNT(DISTINCT ticket_id) AS tickets,
                       SUM(EXTRACT(EPOCH FROM
                           (COALESCE(end_time, NOW()) - start_time)))::bigint AS owned_seconds
                FROM ownership_periods
                WHERE queue_name = ANY(:scope)
                  AND owner IS NOT NULL
                  AND LOWER(owner) NOT IN
                      ('root@localhost','otrs admin (root@localhost)','')
                GROUP BY owner
                ORDER BY tickets DESC LIMIT 10
            """),
            {"scope": scope},
        ).mappings().all()

        owned_total = int(no_own.get("owned_total") or 0) or 1
        no_owner_total = int(no_own.get("no_owner_total") or 0)
        no_owner_pct = round(no_owner_total / owned_total * 100, 2)

    response_avg = (m.get("first_response_time") or m.get("response_time") or {}).get("avg", 0)
    response_n = (m.get("first_response_time") or m.get("response_time") or {}).get("n", 0)
    resol_avg = (m.get("resolution_time") or {}).get("avg", 0)
    wall_resol = m.get("wall_resolution_time") or {}

    return {
        "team": {
            "id": team.id, "name": team.name,
            "queue_prefix": prefix, "queues_extra": queues_extra,
            "color": team.color,
            "response_target_seconds": team.response_target_seconds,
            "resolution_target_seconds": team.resolution_target_seconds,
        },
        "scope_queues": scope,
        "scope_queues_count": len(scope),
        "ticket_counts": {"total": int(total), "open": int(open_n)},
        "metrics": {
            "mtta_seconds": int(response_avg),
            "mttr_seconds": int(resol_avg),
            "response_count": int(response_n),
            "active_breaches": (m.get("resolution_time") or {}).get("breaches", 0),
            "wall_breaches": wall_resol.get("breaches", 0),
            "no_owner_seconds": no_owner_total,
            "no_owner_pct": no_owner_pct,
            "reassignments": int(reassigns),
            "queue_bounces": int(bounces),
        },
        "top_owners": [dict(o) for o in top_owners],
    }
