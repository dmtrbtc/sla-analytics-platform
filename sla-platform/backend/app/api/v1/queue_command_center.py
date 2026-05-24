"""Per-queue operational command center — v2.2 (scope-aware).

Single endpoint that returns EVERYTHING an analyst needs to monitor one
specific production queue:
  - snapshot (ticket counts, age buckets, open/closed/no-owner)
  - SLA metrics (active + wall-clock, response + resolution)
  - top engineers in this queue
  - aging open tickets
  - hour-of-day creation heatmap
  - day-of-week heatmap
  - bounces + re-entry pattern
  - transitions in/out (top 8 each direction)
  - silent breaches scoped to this queue

Built for the 4 critical production queues identified in the prompt:
  MBR-137-Workplace-Veshki / Plaza
  MBR-137-AssetManagement-Veshki / Plaza

Reuses existing services (no business logic duplication) — just a
focused bundling endpoint plus a few queue-scoped SQL queries.

v2.2 — every query honors `?period=24h|1d|7d|30d|90d` or
`?since=...&until=...`. For durational records (queue_periods,
ownership_periods) we use overlap math via scope_filter_sql; for
event/snapshot records we filter by event_time/created_at/computed_at.
When no scope is given, behavior is unchanged (all-time).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from app.core.database import sync_session_factory
from app.core.dependencies import get_current_user
from app.services.forensics.inactivity_engine import InactivityEngine
from app.services.forensics.sla_loss_engine import SLALossEngine
from app.services.forensics.time_scope import (
    TimeScope,
    parse_time_scope,
    scope_filter_sql,
    scope_params,
)

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


SYS_OWNER_FILTER = (
    "(owner IS NULL OR LOWER(owner) IN "
    "('root@localhost','otrs admin (root@localhost)',''))"
)


def _ev_scope() -> str:
    """Scope WHERE fragment for instant-time records (ticket_events.event_time,
    ticket_snapshots.created_at, sla_metrics.computed_at). We treat the
    timestamp as a degenerate interval [t, t]."""
    return "((:since IS NULL OR {col} >= :since) AND (:until IS NULL OR {col} < :until))"


@router.get("/{queue_name:path}")
def queue_command_center(
    queue_name: str,
    period: Optional[str] = Query(None, description="24h | 1d | 7d | 30d | 90d | 365d"),
    since: Optional[str] = Query(None, description="ISO datetime (custom range start)"),
    until: Optional[str] = Query(None, description="ISO datetime (custom range end)"),
) -> dict[str, Any]:
    """Everything the analyst needs about ONE queue, in a single trip."""
    scope: TimeScope = parse_time_scope(period=period, since=since, until=until)
    sp = scope_params(scope)

    # Overlap fragments for durational tables
    QP_SCOPE = scope_filter_sql("qp.entered_at", "qp.exited_at")
    OP_SCOPE = scope_filter_sql("op.start_time", "op.end_time")
    OP2_SCOPE = scope_filter_sql("ownership_periods.start_time", "ownership_periods.end_time")
    # Pure instant-time fragments
    EV_SCOPE_OUT = "((:since IS NULL OR te.event_time >= :since) AND (:until IS NULL OR te.event_time < :until))"
    SNAP_CREATED_SCOPE = "((:since IS NULL OR created_at >= :since) AND (:until IS NULL OR created_at < :until))"
    SLA_METRIC_SCOPE = "((:since IS NULL OR computed_at >= :since) AND (:until IS NULL OR computed_at < :until))"

    with sync_session_factory() as db:
        # Quick existence check — fail fast if the queue is unknown so the
        # frontend can show a clean error instead of an empty payload.
        exists = db.execute(
            text("""
                SELECT 1 FROM ticket_snapshots WHERE current_queue = :q
                UNION ALL
                SELECT 1 FROM queue_periods WHERE queue_name = :q
                LIMIT 1
            """),
            {"q": queue_name},
        ).scalar()
        if not exists:
            raise HTTPException(404, f"Queue '{queue_name}' not found")

        # ── 1. Snapshot ─────────────────────────────────────────────────
        # Snapshot is "live" — the open/closed counts always reflect "now".
        # Scope filters created_at so we count tickets CREATED in the window
        # (analyst expectation for a per-period report).
        snap = db.execute(
            text(f"""
                SELECT
                  COUNT(*) AS total,
                  COUNT(*) FILTER (WHERE is_closed = FALSE) AS open_now,
                  COUNT(*) FILTER (WHERE is_closed = TRUE)  AS closed_now,
                  COUNT(*) FILTER (WHERE is_closed = FALSE AND current_owner IS NULL) AS open_no_owner,
                  COUNT(*) FILTER (WHERE first_response_at IS NOT NULL) AS with_first_response,
                  COUNT(*) FILTER (WHERE is_closed = FALSE
                                   AND created_at < NOW() - INTERVAL '7 days') AS open_over_7d,
                  COUNT(*) FILTER (WHERE is_closed = FALSE
                                   AND created_at < NOW() - INTERVAL '30 days') AS open_over_30d
                FROM ticket_snapshots
                WHERE current_queue = :q
                  AND {SNAP_CREATED_SCOPE}
            """),
            {"q": queue_name, **sp},
        ).mappings().first() or {}

        # ── 2. SLA metrics breakdown ────────────────────────────────────
        # Scope on computed_at so we only count metrics produced in the window.
        sla = db.execute(
            text(f"""
                SELECT metric_name,
                       COUNT(*) AS n,
                       COUNT(*) FILTER (WHERE sla_breached) AS breaches,
                       AVG(metric_seconds)::bigint AS avg_sec,
                       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY metric_seconds) AS p50,
                       PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY metric_seconds) AS p90
                FROM sla_metrics
                WHERE queue_name = :q
                  AND metric_name IN ('first_response_time','resolution_time',
                                      'wall_response_time','wall_resolution_time')
                  AND {SLA_METRIC_SCOPE}
                GROUP BY metric_name
            """),
            {"q": queue_name, **sp},
        ).mappings().all()
        metrics: dict[str, dict] = {}
        for r in sla:
            n = int(r["n"] or 0)
            br = int(r["breaches"] or 0)
            metrics[r["metric_name"]] = {
                "n": n,
                "breaches": br,
                "breach_pct": round(br / n * 100, 2) if n else 0.0,
                "avg_seconds": int(r["avg_sec"] or 0),
                "p50_seconds": int(r["p50"] or 0),
                "p90_seconds": int(r["p90"] or 0),
            }

        # ── 3. Top engineers (non-system) — overlap math on ownership_periods ─
        engineers = db.execute(
            text(f"""
                SELECT op.owner,
                       COUNT(DISTINCT op.ticket_id) AS tickets_held,
                       ROUND(SUM(GREATEST(0, EXTRACT(EPOCH FROM (
                         LEAST(COALESCE(op.end_time, NOW()),
                               COALESCE(:until, COALESCE(op.end_time, NOW())))
                         - GREATEST(op.start_time, COALESCE(:since, op.start_time))
                       ))))/3600, 1) AS hours_owned
                FROM ownership_periods op
                WHERE op.queue_name = :q
                  AND op.owner IS NOT NULL
                  AND NOT (op.owner IS NULL OR LOWER(op.owner) IN
                           ('root@localhost','otrs admin (root@localhost)',''))
                  AND {OP_SCOPE}
                GROUP BY op.owner
                ORDER BY tickets_held DESC LIMIT 10
            """),
            {"q": queue_name, **sp},
        ).mappings().all()

        # ── 4. Aging open tickets ───────────────────────────────────────
        # Aging is "still open NOW" — scope filters which tickets to consider
        # (created in the window) but the age itself is from creation to now.
        aging = db.execute(
            text(f"""
                SELECT ticket_id, ticket_number, title, current_owner,
                       current_state,
                       ROUND(EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400.0, 1) AS age_days,
                       first_response_at
                FROM ticket_snapshots
                WHERE current_queue = :q
                  AND is_closed = FALSE
                  AND {SNAP_CREATED_SCOPE}
                ORDER BY created_at ASC LIMIT 20
            """),
            {"q": queue_name, **sp},
        ).mappings().all()

        # ── 5. Hour-of-day creation distribution ────────────────────────
        hour_dist = db.execute(
            text(f"""
                SELECT EXTRACT(HOUR FROM created_at)::int AS hour,
                       COUNT(*) AS tickets
                FROM ticket_snapshots
                WHERE current_queue = :q
                  AND created_at IS NOT NULL
                  AND {SNAP_CREATED_SCOPE}
                GROUP BY hour ORDER BY hour
            """),
            {"q": queue_name, **sp},
        ).mappings().all()

        # ── 6. Day-of-week ──────────────────────────────────────────────
        dow_dist = db.execute(
            text(f"""
                SELECT EXTRACT(ISODOW FROM created_at)::int AS dow,
                       COUNT(*) AS tickets
                FROM ticket_snapshots
                WHERE current_queue = :q AND created_at IS NOT NULL
                  AND {SNAP_CREATED_SCOPE}
                GROUP BY dow ORDER BY dow
            """),
            {"q": queue_name, **sp},
        ).mappings().all()

        # ── 7. Transitions in/out — scope filters event_time ────────────
        outbound = db.execute(
            text(f"""
                SELECT dest_queue, COUNT(*) AS n,
                       COUNT(DISTINCT ticket_id) AS tickets
                FROM ticket_events te
                WHERE src_queue = :q AND dest_queue IS NOT NULL
                  AND src_queue != dest_queue
                  AND {EV_SCOPE_OUT}
                GROUP BY dest_queue ORDER BY n DESC LIMIT 8
            """),
            {"q": queue_name, **sp},
        ).mappings().all()
        inbound = db.execute(
            text(f"""
                SELECT src_queue, COUNT(*) AS n,
                       COUNT(DISTINCT ticket_id) AS tickets
                FROM ticket_events te
                WHERE dest_queue = :q AND src_queue IS NOT NULL
                  AND src_queue != dest_queue
                  AND {EV_SCOPE_OUT}
                GROUP BY src_queue ORDER BY n DESC LIMIT 8
            """),
            {"q": queue_name, **sp},
        ).mappings().all()

        # ── 8. Bounces — tickets revisiting THIS queue ─────────────────
        # Scope filters segments that overlap the window (overlap-aware)
        bounces = db.execute(
            text(f"""
                SELECT ticket_id, COUNT(*) AS visits
                FROM queue_periods qp
                WHERE qp.queue_name = :q
                  AND {QP_SCOPE}
                GROUP BY ticket_id
                HAVING COUNT(*) >= 2
                ORDER BY visits DESC LIMIT 12
            """),
            {"q": queue_name, **sp},
        ).mappings().all()

        # ── 9. Silent breaches in this queue (delegate to existing engine) ─
        silent = InactivityEngine.detect_silent_breaches(
            db, min_inactivity_ratio=0.5, limit=20, queues=[queue_name], scope=scope,
        )

        # ── 10. Loss attribution share (reuse sla_loss_engine — scope-aware) ─
        all_top = SLALossEngine.top_loss_queues(
            db, limit=200, queues=[queue_name], scope=scope,
        )
        loss_row = all_top[0] if all_top else None

        return {
            "queue_name": queue_name,
            "scope": scope.to_dict(),
            "snapshot": dict(snap),
            "sla_metrics": metrics,
            "engineers": [dict(e) for e in engineers],
            "aging_open_tickets": [
                {**dict(r),
                 "first_response_at": r["first_response_at"].isoformat()
                                       if r["first_response_at"] else None,
                 "age_days": float(r["age_days"] or 0)}
                for r in aging
            ],
            "hour_distribution": [dict(r) for r in hour_dist],
            "dow_distribution": [dict(r) for r in dow_dist],
            "transitions": {
                "outbound": [dict(r) for r in outbound],
                "inbound":  [dict(r) for r in inbound],
            },
            "bounces": [dict(b) for b in bounces],
            "silent_breaches": [s.__dict__ if hasattr(s, "__dict__") else s
                                for s in silent],
            "loss_share": loss_row,  # may be None if queue has no segments
        }
