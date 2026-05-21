"""Queue contribution analysis — Phase 4 v1.5.

For one ticket compute:
  - per-queue wall time, active time, idle time, no-owner time, pause time
  - queue_loss_percent  = (wall_seconds_in_queue / total_wall_seconds) × 100
  - owner_loss_percent  = (owned_seconds_per_owner / total_owned_seconds) × 100

For the whole import compute:
  - routing_instability_score  = mean of (queue_bounce_count × 1.0
                                          + reassignment_count × 0.5)
  - stagnation_score (per ticket)
  - operational_waste_score    = (pause + idle + no_owner) / wall_total
  - transfer_efficiency        = active_after_transfer / wait_after_transfer
  - touch_efficiency           = non_sys_events / wall_hours

All computed in SQL — no per-ticket Python loops.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class QueueContributionRow:
    queue_name: str
    entered_at: Optional[str]
    exited_at: Optional[str]
    wall_seconds: int
    active_seconds: int
    idle_seconds: int
    no_owner_seconds: int
    queue_loss_percent: float
    owners: list[dict[str, Any]]


@dataclass
class OwnerContributionRow:
    owner: str
    owned_seconds: int
    owner_loss_percent: float
    is_system: bool


@dataclass
class TicketContribution:
    ticket_id: int
    total_wall_seconds: int
    queue_contributions: list[QueueContributionRow]
    owner_contributions: list[OwnerContributionRow]
    routing_instability_score: float
    stagnation_score: float
    operational_waste_score: float
    transfer_efficiency: float
    touch_efficiency: float


SYS_OWNER_LIST_SQL = (
    "LOWER(owner) IN ('root@localhost','otrs admin (root@localhost)','')"
)


class ContributionEngine:
    """Per-ticket queue and owner contribution analyzer."""

    @staticmethod
    def for_ticket(db: Session, ticket_id: int) -> TicketContribution:
        # ---- queue contributions ---------------------------------------
        qp_rows = db.execute(
            text(f"""
                WITH qp AS (
                  SELECT qp.queue_name, qp.entered_at, qp.exited_at,
                         COALESCE(qp.duration_seconds,
                                  EXTRACT(EPOCH FROM
                                    (COALESCE(qp.exited_at, NOW()) - qp.entered_at))
                         )::bigint AS wall_seconds
                  FROM queue_periods qp
                  WHERE qp.ticket_id = :tid
                ),
                no_own AS (
                  SELECT op.queue_name,
                         SUM(CASE WHEN op.owner IS NULL
                                  OR {SYS_OWNER_LIST_SQL.replace('owner','op.owner')}
                                  THEN EXTRACT(EPOCH FROM
                                       (COALESCE(op.end_time, NOW()) - op.start_time))
                                  ELSE 0 END)::bigint AS no_owner_seconds
                  FROM ownership_periods op
                  WHERE op.ticket_id = :tid
                  GROUP BY op.queue_name
                ),
                touches AS (
                  SELECT queue_name,
                         COUNT(*) FILTER (WHERE is_system_action IS NOT TRUE)
                           AS touch_count
                  FROM ticket_events
                  WHERE ticket_id = :tid
                  GROUP BY queue_name
                )
                SELECT qp.queue_name, qp.entered_at, qp.exited_at,
                       qp.wall_seconds,
                       COALESCE(no_own.no_owner_seconds, 0) AS no_owner_seconds,
                       COALESCE(touches.touch_count, 0) AS touch_count
                FROM qp
                LEFT JOIN no_own USING (queue_name)
                LEFT JOIN touches USING (queue_name)
                ORDER BY qp.entered_at
            """),
            {"tid": ticket_id},
        ).mappings().all()

        total_wall = sum(int(r["wall_seconds"] or 0) for r in qp_rows) or 1

        # owners per queue (for drill-down)
        own_per_q = db.execute(
            text(f"""
                SELECT queue_name, owner,
                       SUM(EXTRACT(EPOCH FROM
                           (COALESCE(end_time, NOW()) - start_time)))::bigint
                         AS owned_seconds,
                       ({SYS_OWNER_LIST_SQL}) AS is_system
                FROM ownership_periods
                WHERE ticket_id = :tid
                GROUP BY queue_name, owner
                ORDER BY queue_name, owned_seconds DESC
            """),
            {"tid": ticket_id},
        ).mappings().all()
        owners_by_queue: dict[str, list[dict]] = {}
        for r in own_per_q:
            owners_by_queue.setdefault(r["queue_name"] or "", []).append({
                "owner": r["owner"], "owned_seconds": int(r["owned_seconds"] or 0),
                "is_system": bool(r["is_system"]),
            })

        queue_contribs: list[QueueContributionRow] = []
        for r in qp_rows:
            wall = int(r["wall_seconds"] or 0)
            no_own = int(r["no_owner_seconds"] or 0)
            touches = int(r["touch_count"] or 0)
            # Heuristic active = min(wall, 30 min × touches). Same approach
            # as attribution_engine — for now this is a contribution view,
            # not a pause-aware SLA value.
            active = min(wall, touches * 1800)
            idle = max(0, wall - active - no_own)
            queue_contribs.append(QueueContributionRow(
                queue_name=r["queue_name"] or "unknown",
                entered_at=r["entered_at"].isoformat() if r["entered_at"] else None,
                exited_at=r["exited_at"].isoformat() if r["exited_at"] else None,
                wall_seconds=wall, active_seconds=active,
                idle_seconds=idle, no_owner_seconds=no_own,
                queue_loss_percent=round(wall / total_wall * 100, 2),
                owners=owners_by_queue.get(r["queue_name"] or "", []),
            ))

        # ---- owner contributions (aggregate across ticket) -------------
        own_total_row = db.execute(
            text(f"""
                SELECT owner,
                       SUM(EXTRACT(EPOCH FROM
                           (COALESCE(end_time, NOW()) - start_time)))::bigint AS s,
                       ({SYS_OWNER_LIST_SQL}) AS is_system
                FROM ownership_periods
                WHERE ticket_id = :tid
                GROUP BY owner
                ORDER BY s DESC
            """),
            {"tid": ticket_id},
        ).mappings().all()
        total_owned = sum(int(r["s"] or 0) for r in own_total_row) or 1
        owner_contribs = [
            OwnerContributionRow(
                owner=r["owner"] or "—",
                owned_seconds=int(r["s"] or 0),
                owner_loss_percent=round(int(r["s"] or 0) / total_owned * 100, 2),
                is_system=bool(r["is_system"]),
            )
            for r in own_total_row
        ]

        # ---- scores ----------------------------------------------------
        # routing_instability_score: bounces × 1 + reassigns × 0.5
        bounces = db.execute(
            text("""
                SELECT COUNT(*) FROM ticket_events WHERE ticket_id = :tid
                AND src_queue IS NOT NULL AND dest_queue IS NOT NULL
                AND src_queue != dest_queue
            """),
            {"tid": ticket_id},
        ).scalar() or 0
        reassigns = db.execute(
            text("""
                SELECT COUNT(*) FROM ticket_events WHERE ticket_id = :tid
                AND new_owner IS NOT NULL AND old_owner IS NOT NULL
                AND new_owner != old_owner
            """),
            {"tid": ticket_id},
        ).scalar() or 0
        routing_instability = round(float(bounces) * 1.0 + float(reassigns) * 0.5, 2)

        # stagnation_score: longest gap between non-system events / total wall
        longest_gap = db.execute(
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
            {"tid": ticket_id},
        ).scalar() or 0
        stagnation = round(min(1.0, float(longest_gap) / max(1, total_wall)), 4)

        # operational_waste = (no-owner + idle + pause) / wall
        no_own_total = sum(qc.no_owner_seconds for qc in queue_contribs)
        idle_total = sum(qc.idle_seconds for qc in queue_contribs)
        pause_total = db.execute(
            text("""
                SELECT COALESCE(SUM(metric_seconds), 0)::bigint
                FROM sla_metrics
                WHERE ticket_id = :tid AND metric_name = 'pause_seconds'
            """),
            {"tid": ticket_id},
        ).scalar() or 0
        # Pause is measured on the creation→resolution window while
        # idle/no_owner are measured per queue_period — they can overlap when
        # a ticket is paused inside an unowned queue. We clamp to 100 to keep
        # the score interpretable. The raw breakdown remains in the payload.
        op_waste = round(min(100.0,
            (float(no_own_total + idle_total + pause_total) / total_wall) * 100
        ), 2)

        # transfer_efficiency: fraction of post-Move time that's followed by a
        # human (non-system) event within 1 hour, else system-only.
        eff_row = db.execute(
            text("""
                WITH e AS (
                  SELECT event_time, event_type, is_system_action,
                         LEAD(event_time) OVER (ORDER BY event_time) AS next_t,
                         LEAD(is_system_action) OVER (ORDER BY event_time) AS next_sys
                  FROM ticket_events WHERE ticket_id = :tid
                )
                SELECT
                  COUNT(*) FILTER (WHERE LOWER(event_type)='move') AS moves,
                  COUNT(*) FILTER (WHERE LOWER(event_type)='move'
                                   AND next_sys IS FALSE
                                   AND (next_t - event_time) < INTERVAL '1 hour'
                                  ) AS fast_human_follows
                FROM e
            """),
            {"tid": ticket_id},
        ).mappings().first() or {}
        moves = int(eff_row.get("moves") or 0)
        fast = int(eff_row.get("fast_human_follows") or 0)
        xfer_eff = round((fast / moves) if moves else 1.0, 4)

        # touch_efficiency: non-system events per hour of wall time
        non_sys = db.execute(
            text("""
                SELECT COUNT(*) FROM ticket_events
                WHERE ticket_id = :tid
                  AND (is_system_action IS NULL OR is_system_action IS FALSE)
            """),
            {"tid": ticket_id},
        ).scalar() or 0
        touch_eff = round(float(non_sys) / (total_wall / 3600.0), 4) if total_wall else 0.0

        return TicketContribution(
            ticket_id=ticket_id,
            total_wall_seconds=int(total_wall),
            queue_contributions=queue_contribs,
            owner_contributions=owner_contribs,
            routing_instability_score=routing_instability,
            stagnation_score=stagnation,
            operational_waste_score=op_waste,
            transfer_efficiency=xfer_eff,
            touch_efficiency=touch_eff,
        )
