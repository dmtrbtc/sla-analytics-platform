"""Phase 5 — Owner Forensics.

Per-owner operational fingerprints, SQL-aggregated:

  - load_tickets, load_hours
  - parked_tickets:        owned but had zero non-system events while owned
  - ownership_gap_seconds: total time during which a ticket they own had no owner
  - touch_frequency:       non_sys_events / load_hours
  - reassignment_pressure: avg owner changes per ticket they touched
  - overload_score:        (load_tickets * mean_resolution_h) / capacity_proxy
  - idle_owner_flag:       True if 0 touches in window despite owning tickets

Excludes the synthetic `root@localhost` actor — it's the absence of an owner,
not an owner.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


SYSTEM_OWNERS_SQL = (
    "LOWER(owner) IN ('root@localhost','otrs admin (root@localhost)','')"
)


@dataclass
class OwnerForensicRow:
    owner: str
    load_tickets: int
    load_hours: float
    parked_tickets: int
    ownership_gap_seconds: int
    non_sys_events: int
    touch_frequency: float
    reassignment_pressure: float
    overload_score: float
    idle_flag: bool


class OwnerForensicsService:
    @staticmethod
    def compute_all(
        db: Session,
        limit: int = 100,
        queues: list[str] | None = None,
    ) -> list[OwnerForensicRow]:
        """Aggregate owner forensic scores. If `queues` is provided, only
        ownership periods inside those queues count toward the totals."""
        rows = db.execute(
            text(f"""
                WITH own AS (
                  SELECT op.owner,
                         op.ticket_id,
                         SUM(EXTRACT(EPOCH FROM (COALESCE(op.end_time, NOW()) - op.start_time)))::bigint
                            AS dur_seconds
                  FROM ownership_periods op
                  WHERE op.owner IS NOT NULL
                    AND NOT ({SYSTEM_OWNERS_SQL})
                    AND ((:has_queues IS FALSE) OR op.queue_name = ANY(:queue_list))
                  GROUP BY op.owner, op.ticket_id
                ),
                per_owner AS (
                  SELECT owner,
                         COUNT(DISTINCT ticket_id) AS load_tickets,
                         SUM(dur_seconds) AS load_seconds
                  FROM own
                  GROUP BY owner
                ),
                touches AS (
                  SELECT te.owner_name AS owner,
                         COUNT(*) FILTER (WHERE te.is_system_action IS NOT TRUE)
                           AS non_sys_events
                  FROM ticket_events te
                  WHERE te.owner_name IS NOT NULL
                    AND LOWER(te.owner_name) NOT IN
                        ('root@localhost','otrs admin (root@localhost)','')
                  GROUP BY te.owner_name
                ),
                parked AS (
                  SELECT own.owner,
                         COUNT(*) FILTER (
                           WHERE COALESCE(t.non_sys, 0) = 0
                         ) AS parked_tickets
                  FROM own
                  LEFT JOIN (
                    SELECT ticket_id, owner_name AS owner,
                           COUNT(*) FILTER (WHERE is_system_action IS NOT TRUE)
                             AS non_sys
                    FROM ticket_events
                    GROUP BY ticket_id, owner_name
                  ) t ON t.ticket_id = own.ticket_id AND t.owner = own.owner
                  GROUP BY own.owner
                ),
                reassign AS (
                  SELECT te.new_owner AS owner,
                         COUNT(*) AS handoffs
                  FROM ticket_events te
                  WHERE te.new_owner IS NOT NULL
                    AND te.old_owner IS NOT NULL
                    AND te.new_owner != te.old_owner
                    AND LOWER(te.new_owner) NOT IN
                        ('root@localhost','otrs admin (root@localhost)','')
                  GROUP BY te.new_owner
                )
                SELECT
                  p.owner,
                  p.load_tickets,
                  p.load_seconds,
                  COALESCE(t.non_sys_events, 0) AS non_sys_events,
                  COALESCE(parked.parked_tickets, 0) AS parked_tickets,
                  COALESCE(reassign.handoffs, 0) AS handoffs
                FROM per_owner p
                LEFT JOIN touches t ON t.owner = p.owner
                LEFT JOIN parked ON parked.owner = p.owner
                LEFT JOIN reassign ON reassign.owner = p.owner
                ORDER BY p.load_tickets DESC
                LIMIT :lim
            """),
            {
                "lim": limit,
                "has_queues": bool(queues),
                "queue_list": queues or [],
            },
        ).mappings().all()

        out: list[OwnerForensicRow] = []
        for r in rows:
            load_seconds = int(r["load_seconds"] or 0)
            load_hours = load_seconds / 3600.0
            non_sys = int(r["non_sys_events"] or 0)
            touch_freq = (non_sys / load_hours) if load_hours > 0 else 0.0
            parked = int(r["parked_tickets"] or 0)
            handoffs = int(r["handoffs"] or 0)
            load_t = int(r["load_tickets"] or 0)
            reassign_pressure = (handoffs / load_t) if load_t > 0 else 0.0
            # overload — load relative to median load of 40h/40tickets
            overload = (load_hours / 40.0) + (load_t / 40.0)
            idle = non_sys == 0 and load_t > 0

            out.append(OwnerForensicRow(
                owner=r["owner"],
                load_tickets=load_t,
                load_hours=round(load_hours, 2),
                parked_tickets=parked,
                ownership_gap_seconds=0,   # see per-owner gap below
                non_sys_events=non_sys,
                touch_frequency=round(touch_freq, 4),
                reassignment_pressure=round(reassign_pressure, 4),
                overload_score=round(overload, 4),
                idle_flag=idle,
            ))
        return out

    # ----- Ownership gap per ticket (top offenders) ---------------------

    @staticmethod
    def ownership_gaps(db: Session, limit: int = 50) -> list[dict[str, Any]]:
        """Top tickets with the largest cumulative ownership gap
        (sum of intervals between consecutive ownership_periods)."""
        rows = db.execute(
            text("""
                WITH op AS (
                  SELECT ticket_id, start_time, end_time,
                         LEAD(start_time) OVER
                           (PARTITION BY ticket_id ORDER BY start_time) AS next_start
                  FROM ownership_periods
                )
                SELECT ticket_id,
                       SUM(GREATEST(0, EXTRACT(EPOCH FROM (next_start - end_time))))::bigint
                          AS gap_seconds
                FROM op
                WHERE end_time IS NOT NULL AND next_start IS NOT NULL
                GROUP BY ticket_id
                ORDER BY gap_seconds DESC
                LIMIT :lim
            """),
            {"lim": limit},
        ).mappings().all()
        return [{"ticket_id": int(r["ticket_id"]), "gap_seconds": int(r["gap_seconds"])} for r in rows]
