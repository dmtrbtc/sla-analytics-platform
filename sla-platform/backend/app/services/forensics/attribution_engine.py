"""Forensic Attribution Engine — Phases 1 & 2.

Phase 1 — DUAL SLA MODEL
  ACTIVE SLA (existing V2 metrics):     business-hours aware, pause-subtracted
  WALL-CLOCK SLA (new):                 raw elapsed seconds, no pause subtraction
  Both surfaced as new metric names so dashboards can compare delta = wall - active.

Phase 2 — QUEUE BLAME ALGORITHM
  Each QueuePeriod gets:
    - active_seconds, wall_seconds
    - idle_ratio       = unowned_seconds / wall_seconds
    - no_owner_ratio   = root_owner_seconds / wall_seconds
    - bounce_count     = how many times the ticket re-entered this same queue
    - stagnation_score = wall_seconds without any agent event
    - overdue_ratio    = wall_seconds / sla_target_seconds (capped)

  queue_blame_score = weighted sum of normalized signals (0..100)
    0.30 * (wall_seconds / total_wall)
    0.20 * idle_ratio
    0.20 * no_owner_ratio
    0.15 * stagnation_score_norm
    0.10 * bounce_count_norm
    0.05 * overdue_ratio

  Breach root cause is assigned to the queue with the highest blame_score at the
  moment the deadline was crossed (wall-clock crossing), NOT to current_queue.

All computations are pure SQL aggregation; no Python O(N) per-ticket loops.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.models import (
    SLADefinition,
    SLAMetric,
    SLAQueueRule,
    TicketSnapshot,
)
from app.services.sla.metrics_engine import _get_active_queue_rules
from app.services.sla.pause_engine import calculate_active_time

logger = logging.getLogger(__name__)


# ---------- Public dataclasses ---------------------------------------------


@dataclass
class QueueBlameRow:
    queue_name: str
    entered_at: datetime
    exited_at: Optional[datetime]
    active_seconds: int
    wall_seconds: int
    idle_seconds: int
    no_owner_seconds: int
    bounce_count: int
    stagnation_score: float
    overdue_ratio: float
    blame_score: float


@dataclass
class BreachRootCause:
    ticket_id: int
    metric_name: str               # "first_response_time" | "resolution_time"
    breach_queue: Optional[str]
    breach_owner: Optional[str]
    breach_transition: Optional[str]   # "queueA → queueB" or None
    breach_reason: str             # see REASONS
    breach_at: Optional[datetime]
    queue_blame_score: float
    owner_blame_score: float
    contributing_queues: list[dict[str, Any]] = field(default_factory=list)
    contributing_owners: list[dict[str, Any]] = field(default_factory=list)


# ---------- Reason taxonomy -------------------------------------------------

BREACH_REASONS = (
    "queue_overload",          # queue has many concurrent breaching tickets
    "no_owner",                # blame-queue had >80% no-owner time during breach window
    "transfer_delay",          # ticket waited >X% of SLA after a Move event
    "bounce_loop",             # >=3 re-entries of same queue
    "reassignment_storm",      # >=3 owner changes
    "waiting_state_abuse",     # >70% time in pending* states
    "unresolved_pause",        # active pause never resumed
    "routing_chaos",           # blame queue has high routing entropy
    "stagnation",              # no events for > 50% of SLA target
    "no_activity",             # zero events in last_activity_age window
)


# ---------- The engine ------------------------------------------------------


class ForensicAttributionEngine:
    """Computes per-ticket forensic SLA attribution.

    Stateless service — all state lives in DB. Use the classmethods directly.
    """

    # ----- Phase 1: wall-clock metrics ----------------------------------

    @staticmethod
    def compute_wall_clock_metrics(
        db: Session,
        ticket: TicketSnapshot,
        sla_def: SLADefinition,
        import_id: str,
    ) -> list[SLAMetric]:
        """Emit wall-clock counterparts for response and resolution.

        Backwards-compatible: writes new metric_name values
        ("wall_response_time", "wall_resolution_time") into the existing
        sla_metrics table. Old metrics ("first_response_time",
        "resolution_time") remain untouched.
        """
        metrics: list[SLAMetric] = []

        if ticket.created_at and ticket.first_response_at:
            wall = max(0, int((ticket.first_response_at - ticket.created_at).total_seconds()))
            tgt = _resolve_target(db, ticket, sla_def, "response_target_seconds")
            metrics.append(
                _build(ticket, sla_def, import_id, "wall_response_time", wall, tgt)
            )

        end = ticket.resolution_at or ticket.updated_at or datetime.now(timezone.utc)
        if ticket.created_at:
            wall = max(0, int((end - ticket.created_at).total_seconds()))
            tgt = _resolve_target(db, ticket, sla_def, "resolution_target_seconds")
            metrics.append(
                _build(
                    ticket, sla_def, import_id, "wall_resolution_time", wall, tgt,
                    is_open=not ticket.is_closed,
                )
            )

        # pause / idle / no-owner / ownership-gap / transfer-wait / stagnation
        extra = _compute_loss_buckets(db, ticket, sla_def, import_id)
        metrics.extend(extra)

        return metrics

    # ----- Phase 2: queue blame -----------------------------------------

    @staticmethod
    def compute_queue_blame(
        db: Session, ticket_id: int, sla_target_seconds: int = 0,
    ) -> list[QueueBlameRow]:
        """Per-queue blame rows for a single ticket. SQL aggregated."""
        rows = db.execute(
            text("""
                WITH qp AS (
                  SELECT
                    qp.queue_name,
                    qp.entered_at,
                    qp.exited_at,
                    COALESCE(qp.duration_seconds,
                             EXTRACT(EPOCH FROM (COALESCE(qp.exited_at, NOW()) - qp.entered_at))
                            )::bigint AS wall_seconds
                  FROM queue_periods qp
                  WHERE qp.ticket_id = :tid
                ),
                op AS (
                  SELECT
                    op.queue_name,
                    op.start_time, op.end_time,
                    op.owner,
                    EXTRACT(EPOCH FROM (COALESCE(op.end_time, NOW()) - op.start_time))::bigint AS dur
                  FROM ownership_periods op
                  WHERE op.ticket_id = :tid
                ),
                no_owner_per_q AS (
                  SELECT queue_name,
                         SUM(CASE WHEN owner IS NULL
                                  OR LOWER(owner) IN ('root@localhost','otrs admin (root@localhost)','')
                                  THEN dur ELSE 0 END)::bigint AS no_owner_seconds
                  FROM op
                  GROUP BY queue_name
                ),
                bounces AS (
                  SELECT queue_name, COUNT(*) - 1 AS bounce_count
                  FROM qp
                  GROUP BY queue_name
                ),
                touches AS (
                  SELECT te.queue_name,
                         COUNT(*) FILTER (WHERE te.is_system_action IS NOT TRUE) AS touch_count
                  FROM ticket_events te
                  WHERE te.ticket_id = :tid
                  GROUP BY te.queue_name
                )
                SELECT
                  qp.queue_name,
                  qp.entered_at,
                  qp.exited_at,
                  qp.wall_seconds,
                  COALESCE(no_owner_per_q.no_owner_seconds, 0) AS no_owner_seconds,
                  COALESCE(bounces.bounce_count, 0) AS bounce_count,
                  COALESCE(touches.touch_count, 0) AS touch_count
                FROM qp
                LEFT JOIN no_owner_per_q USING (queue_name)
                LEFT JOIN bounces USING (queue_name)
                LEFT JOIN touches USING (queue_name)
                ORDER BY qp.entered_at
            """),
            {"tid": ticket_id},
        ).mappings().all()

        total_wall = sum(r["wall_seconds"] or 0 for r in rows) or 1
        max_bounce = max((r["bounce_count"] or 0 for r in rows), default=0) or 1

        out: list[QueueBlameRow] = []
        for r in rows:
            wall = int(r["wall_seconds"] or 0)
            no_own = int(r["no_owner_seconds"] or 0)
            touches = int(r["touch_count"] or 0)
            idle = max(0, wall - min(wall, _approx_active(wall, touches)))
            stagnation = 1.0 if touches == 0 and wall > 0 else max(0.0, 1.0 - touches / max(wall / 3600.0, 1))
            no_own_ratio = (no_own / wall) if wall > 0 else 0.0
            idle_ratio = (idle / wall) if wall > 0 else 0.0
            overdue = (wall / sla_target_seconds) if sla_target_seconds else 0.0
            bounce_n = int(r["bounce_count"] or 0)

            blame = (
                0.30 * (wall / total_wall)
                + 0.20 * idle_ratio
                + 0.20 * no_own_ratio
                + 0.15 * min(1.0, stagnation)
                + 0.10 * (bounce_n / max_bounce)
                + 0.05 * min(1.0, overdue)
            ) * 100.0

            out.append(QueueBlameRow(
                queue_name=r["queue_name"] or "unknown",
                entered_at=r["entered_at"],
                exited_at=r["exited_at"],
                active_seconds=max(0, wall - idle),
                wall_seconds=wall,
                idle_seconds=idle,
                no_owner_seconds=no_own,
                bounce_count=bounce_n,
                stagnation_score=round(stagnation, 4),
                overdue_ratio=round(overdue, 4),
                blame_score=round(blame, 2),
            ))
        return out

    # ----- Phase 2: breach root cause -----------------------------------

    @staticmethod
    def compute_breach_root_cause(
        db: Session,
        ticket: TicketSnapshot,
        sla_def: SLADefinition,
        metric_name: str = "resolution_time",
    ) -> BreachRootCause:
        """Determine WHICH queue/owner held the ticket when SLA crossed.

        We use wall-clock deadline: created_at + target_seconds.
        Whichever QueuePeriod covers that timestamp gets the breach.
        If no queue period covers it (e.g. ticket already closed), we fall
        back to the highest-blame queue.
        """
        if metric_name == "first_response_time":
            target = _resolve_target(db, ticket, sla_def, "response_target_seconds")
            anchor = ticket.created_at
        else:
            target = _resolve_target(db, ticket, sla_def, "resolution_target_seconds")
            anchor = ticket.created_at

        deadline = None
        if anchor and target > 0:
            from datetime import timedelta
            deadline = anchor + timedelta(seconds=target)

        blame_rows = ForensicAttributionEngine.compute_queue_blame(db, ticket.ticket_id, target)
        contributing = sorted(blame_rows, key=lambda b: b.blame_score, reverse=True)

        breach_queue: Optional[str] = None
        breach_at = deadline
        if deadline:
            for b in blame_rows:
                exited = b.exited_at or datetime.now(timezone.utc)
                # naive comparability — drop tz if needed
                _entered = _naive(b.entered_at)
                _exited = _naive(exited)
                _deadline = _naive(deadline)
                if _entered <= _deadline <= _exited:
                    breach_queue = b.queue_name
                    break

        if not breach_queue and contributing:
            breach_queue = contributing[0].queue_name

        # owner blame at breach moment
        owner_row = None
        if deadline:
            owner_row = db.execute(
                text("""
                    SELECT owner, start_time, end_time
                    FROM ownership_periods
                    WHERE ticket_id = :tid
                      AND start_time <= :dl
                      AND (end_time IS NULL OR end_time >= :dl)
                    ORDER BY start_time DESC LIMIT 1
                """),
                {"tid": ticket.ticket_id, "dl": _naive(deadline)},
            ).mappings().first()

        breach_owner = owner_row["owner"] if owner_row else None

        # transition straddling deadline
        transition_row = None
        if deadline:
            transition_row = db.execute(
                text("""
                    SELECT src_queue, dest_queue, event_time
                    FROM ticket_events
                    WHERE ticket_id = :tid
                      AND src_queue IS NOT NULL AND dest_queue IS NOT NULL
                      AND src_queue != dest_queue
                    ORDER BY ABS(EXTRACT(EPOCH FROM (event_time - :dl))) ASC
                    LIMIT 1
                """),
                {"tid": ticket.ticket_id, "dl": _naive(deadline)},
            ).mappings().first()

        transition = None
        if transition_row:
            transition = f"{transition_row['src_queue']} → {transition_row['dest_queue']}"

        reason = _infer_reason(db, ticket.ticket_id, contributing, breach_queue, target)
        queue_blame = contributing[0].blame_score if contributing else 0.0
        owner_blame = _owner_blame(db, ticket.ticket_id, breach_owner, target)

        return BreachRootCause(
            ticket_id=ticket.ticket_id,
            metric_name=metric_name,
            breach_queue=breach_queue,
            breach_owner=breach_owner,
            breach_transition=transition,
            breach_reason=reason,
            breach_at=deadline,
            queue_blame_score=queue_blame,
            owner_blame_score=owner_blame,
            contributing_queues=[
                {
                    "queue": b.queue_name,
                    "wall_seconds": b.wall_seconds,
                    "no_owner_seconds": b.no_owner_seconds,
                    "bounce_count": b.bounce_count,
                    "stagnation_score": b.stagnation_score,
                    "blame_score": b.blame_score,
                }
                for b in contributing[:10]
            ],
            contributing_owners=_top_owners(db, ticket.ticket_id),
        )


# ---------- Helpers ---------------------------------------------------------


def _naive(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _resolve_target(
    db: Session,
    ticket: TicketSnapshot,
    sla_def: SLADefinition,
    field: str,
) -> int:
    """V3: still allows queue-rule override, but the breach is attributed
    to the queue at deadline crossing — not to current_queue."""
    if not ticket.current_queue:
        return getattr(sla_def, field, 0)
    import fnmatch
    for rule in _get_active_queue_rules(db):
        if fnmatch.fnmatch(ticket.current_queue, rule.queue_pattern):
            v = getattr(rule, field, None)
            if v is not None:
                return v
    return getattr(sla_def, field, 0)


def _build(
    ticket: TicketSnapshot,
    sla_def: SLADefinition,
    import_id: str,
    metric_name: str,
    seconds: int,
    target: int,
    is_open: bool = False,
) -> SLAMetric:
    breached = target > 0 and seconds > target
    risk_score = None
    risk_level = None
    risk_reason = None
    if target > 0:
        ratio = seconds / target
        if ratio >= 1.0:
            risk_score = min(100, int(ratio * 100))
            risk_level = "breached"
            risk_reason = f"wall-clock SLA breached at {ratio:.0%}"
        elif ratio >= 0.95:
            risk_score = 95
            risk_level = "critical"
            risk_reason = f"wall-clock {ratio:.0%} of target"
        elif ratio >= 0.80:
            risk_score = int(ratio * 100)
            risk_level = "high"
            risk_reason = f"wall-clock {ratio:.0%} of target"
    return SLAMetric(
        ticket_id=ticket.ticket_id,
        metric_name=metric_name,
        metric_seconds=seconds,
        sla_breached=breached,
        sla_risk_score=risk_score,
        risk_level=risk_level,
        risk_reason=risk_reason,
        sla_definition_id=sla_def.id,
        import_id=UUID(import_id) if isinstance(import_id, str) else import_id,
        queue_name=ticket.current_queue,
        owner=ticket.current_owner,
        confidence=ticket.confidence,
        computed_at=datetime.now(timezone.utc),
    )


def _compute_loss_buckets(
    db: Session,
    ticket: TicketSnapshot,
    sla_def: SLADefinition,
    import_id: str,
) -> list[SLAMetric]:
    """pause_seconds, idle_seconds, no_owner_seconds, ownership_gap_seconds,
    transfer_wait_seconds, stagnation_seconds — emitted as separate metrics."""
    if not ticket.created_at:
        return []
    end = ticket.resolution_at or ticket.updated_at or datetime.now(timezone.utc)
    bh_config = sla_def.business_hours if sla_def.business_hours_only else None
    active = calculate_active_time(
        db, ticket.ticket_id, import_id, [(ticket.created_at, end)], bh_config,
    )
    pause_seconds = int(active.get("paused_time_seconds") or 0)
    active_seconds = int(active.get("active_time_seconds") or 0)
    wall_seconds = pause_seconds + active_seconds

    # no_owner_seconds from ownership_periods
    no_owner = db.execute(
        text("""
            SELECT COALESCE(SUM(
                EXTRACT(EPOCH FROM (COALESCE(end_time, NOW()) - start_time))
            ), 0)::bigint AS s
            FROM ownership_periods
            WHERE ticket_id = :tid
              AND (owner IS NULL
                   OR LOWER(owner) IN ('root@localhost','otrs admin (root@localhost)',''))
        """),
        {"tid": ticket.ticket_id},
    ).scalar() or 0

    # ownership_gap_seconds — gaps between consecutive ownership_periods
    gap_rows = db.execute(
        text("""
            SELECT start_time, end_time FROM ownership_periods
            WHERE ticket_id = :tid ORDER BY start_time
        """),
        {"tid": ticket.ticket_id},
    ).mappings().all()
    ownership_gap = 0
    prev_end = None
    for row in gap_rows:
        st = row["start_time"]
        if prev_end and st and st > prev_end:
            ownership_gap += int((st - prev_end).total_seconds())
        prev_end = row["end_time"] or prev_end

    # transfer_wait_seconds — sum of intervals between a Move event and the next non-system event
    transfer_wait = db.execute(
        text("""
            WITH e AS (
              SELECT event_time, event_type, is_system_action,
                     LEAD(event_time) OVER (ORDER BY event_time) AS next_t,
                     LEAD(is_system_action) OVER (ORDER BY event_time) AS next_sys
              FROM ticket_events WHERE ticket_id = :tid
            )
            SELECT COALESCE(SUM(EXTRACT(EPOCH FROM (next_t - event_time))), 0)::bigint
            FROM e
            WHERE LOWER(event_type) = 'move'
              AND next_t IS NOT NULL
              AND (next_sys IS TRUE OR next_sys IS NULL)
        """),
        {"tid": ticket.ticket_id},
    ).scalar() or 0

    # stagnation_seconds — longest stretch with no non-system event
    stagnation = db.execute(
        text("""
            WITH e AS (
              SELECT event_time,
                     LAG(event_time) OVER (ORDER BY event_time) AS prev_t
              FROM ticket_events
              WHERE ticket_id = :tid
                AND (is_system_action IS NULL OR is_system_action IS FALSE)
            )
            SELECT COALESCE(MAX(EXTRACT(EPOCH FROM (event_time - prev_t))), 0)::bigint
            FROM e
        """),
        {"tid": ticket.ticket_id},
    ).scalar() or 0

    idle_seconds = max(0, wall_seconds - active_seconds - int(no_owner))

    base = lambda name, s: SLAMetric(
        ticket_id=ticket.ticket_id,
        metric_name=name,
        metric_seconds=int(s),
        sla_definition_id=sla_def.id,
        import_id=UUID(import_id) if isinstance(import_id, str) else import_id,
        queue_name=ticket.current_queue,
        owner=ticket.current_owner,
        confidence=ticket.confidence,
        computed_at=datetime.now(timezone.utc),
    )
    return [
        base("pause_seconds", pause_seconds),
        base("idle_seconds", idle_seconds),
        base("no_owner_seconds", no_owner),
        base("ownership_gap_seconds", ownership_gap),
        base("transfer_wait_seconds", transfer_wait),
        base("stagnation_seconds", stagnation),
    ]


def _approx_active(wall_seconds: int, touches: int) -> int:
    """Heuristic — assume each agent touch buys ~30 min of active work,
    capped by wall_seconds. This is for blame-ratio only; precise active
    time still comes from pause_engine.calculate_active_time."""
    if touches <= 0:
        return 0
    return min(wall_seconds, touches * 1800)


def _infer_reason(
    db: Session,
    ticket_id: int,
    contributing: list[QueueBlameRow],
    breach_queue: Optional[str],
    target: int,
) -> str:
    """Pick the dominant breach reason from the taxonomy."""
    if not contributing:
        return "no_activity"

    top = contributing[0]

    if top.no_owner_seconds and top.wall_seconds and (top.no_owner_seconds / top.wall_seconds) > 0.80:
        return "no_owner"
    if top.bounce_count >= 3:
        return "bounce_loop"
    if top.stagnation_score >= 0.8 and top.wall_seconds > (target * 0.5 if target else 0):
        return "stagnation"
    if top.overdue_ratio > 2.0:
        return "queue_overload"

    # reassignment storm
    reassigns = db.execute(
        text("""
            SELECT COUNT(*) FROM ticket_events
            WHERE ticket_id = :tid
              AND new_owner IS NOT NULL AND old_owner IS NOT NULL
              AND new_owner != old_owner
        """),
        {"tid": ticket_id},
    ).scalar() or 0
    if reassigns >= 3:
        return "reassignment_storm"

    # waiting state abuse
    pending_row = db.execute(
        text("""
            SELECT COALESCE(SUM(metric_seconds), 0) AS p
            FROM sla_metrics
            WHERE ticket_id = :tid AND metric_name = 'pause_seconds'
        """),
        {"tid": ticket_id},
    ).scalar() or 0
    if pending_row and target and (pending_row / target) > 0.70:
        return "waiting_state_abuse"

    # any Move events at all?
    moves = db.execute(
        text("""
            SELECT COUNT(*) FROM ticket_events
            WHERE ticket_id = :tid
              AND src_queue IS NOT NULL AND dest_queue IS NOT NULL
              AND src_queue != dest_queue
        """),
        {"tid": ticket_id},
    ).scalar() or 0
    if moves >= 5 and len({c.queue_name for c in contributing}) >= 4:
        return "routing_chaos"
    if moves >= 1 and top.wall_seconds > (target * 0.3 if target else 0):
        return "transfer_delay"

    # any non-system events at all?
    touches = db.execute(
        text("""
            SELECT COUNT(*) FROM ticket_events
            WHERE ticket_id = :tid
              AND (is_system_action IS NULL OR is_system_action IS FALSE)
        """),
        {"tid": ticket_id},
    ).scalar() or 0
    if touches == 0:
        return "no_activity"

    return "stagnation"


def _owner_blame(db: Session, ticket_id: int, owner: Optional[str], target: int) -> float:
    if not owner:
        return 0.0
    row = db.execute(
        text("""
            SELECT COALESCE(SUM(
              EXTRACT(EPOCH FROM (COALESCE(end_time, NOW()) - start_time))
            ), 0)::bigint AS s
            FROM ownership_periods
            WHERE ticket_id = :tid AND owner = :o
        """),
        {"tid": ticket_id, "o": owner},
    ).scalar() or 0
    if not target:
        return 0.0
    ratio = (int(row) / target) if target else 0
    return round(min(100.0, ratio * 100.0), 2)


def _top_owners(db: Session, ticket_id: int) -> list[dict[str, Any]]:
    rows = db.execute(
        text("""
            SELECT owner,
                   COALESCE(SUM(
                     EXTRACT(EPOCH FROM (COALESCE(end_time, NOW()) - start_time))
                   ), 0)::bigint AS dur
            FROM ownership_periods
            WHERE ticket_id = :tid
            GROUP BY owner
            ORDER BY dur DESC
            LIMIT 5
        """),
        {"tid": ticket_id},
    ).mappings().all()
    return [{"owner": r["owner"], "seconds": int(r["dur"])} for r in rows]
