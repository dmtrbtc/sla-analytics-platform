"""Phase 4 — Queue Forensics.

Operational fingerprints per queue, computed in SQL:

  - entropy:                Shannon entropy of outbound queue routing (bits).
                            High = chaotic dispatch; low = deterministic routing.
  - routing_chaos_score:    entropy normalized by log2(unique_targets).
  - parking_lot_score:      no_owner_ratio × low_touch_rate × long_stay.
                            High when tickets enter and sit unowned.
  - black_hole_score:       parking_lot_score × breach_rate × low_exit_rate.
                            A black hole is a parking lot that also breaches and
                            doesn't release tickets.
  - stagnation_score:       fraction of holding time without any non-system event.
  - transfer_loop_score:    re-entries / total entries (bounce density).
  - pressure_score:         concurrent_breaching_tickets / open_capacity_proxy.

Real-data thresholds (from D:\\SLA_test forensic baseline):
  black_hole:    score >= 0.5 (calibrated on MBR-137-SAP_Basis_support et al.)
  parking_lot:   no_owner_ratio >= 0.95 AND touch_rate <= 0.5 per hour
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.forensics.time_scope import (
    TimeScope,
    scope_filter_sql,
    scope_params,
)

logger = logging.getLogger(__name__)


def _scope_binds(scope: Optional[TimeScope]) -> dict:
    """Return {since, until} binds suitable for embedding in scope-aware SQL."""
    if scope is None:
        return {"since": None, "until": None}
    return scope_params(scope)


@dataclass
class QueueForensicRow:
    queue: str
    total_tickets: int
    total_wall_hours: float
    mean_stay_hours: float
    p90_stay_hours: float
    no_owner_ratio: float
    touch_rate_per_hour: float
    entropy_bits: float
    unique_targets: int
    routing_chaos_score: float
    parking_lot_score: float
    black_hole_score: float
    stagnation_score: float
    transfer_loop_score: float
    pressure_score: float
    breach_count: int
    breach_rate: float


class QueueForensicsService:
    @staticmethod
    def compute_all(
        db: Session,
        limit: int = 100,
        queues: list[str] | None = None,
        scope: Optional[TimeScope] = None,
    ) -> list[QueueForensicRow]:
        """Per-queue forensic scores. If `queues` is given, restrict output
        to that set (and bump the SQL `LIMIT` so we don't lose them before
        filtering).

        When `scope` is provided, durational records (queue_periods,
        ownership_periods) are restricted to segments that overlap the
        window, and event/metric records use instant-time filtering on
        their primary timestamp.
        """
        qp_scope = scope_filter_sql("qp.entered_at", "qp.exited_at")
        op_scope = scope_filter_sql("op.start_time", "op.end_time")
        ev_scope = "(:since IS NULL OR te.event_time >= :since) AND (:until IS NULL OR te.event_time < :until)"
        m_scope = "(:since IS NULL OR m.computed_at >= :since) AND (:until IS NULL OR m.computed_at < :until)"
        qp_inner_scope = scope_filter_sql("entered_at", "exited_at")
        base = db.execute(
            text(f"""
                WITH qp_agg AS (
                  SELECT
                    qp.queue_name,
                    COUNT(*) AS segments,
                    COUNT(DISTINCT qp.ticket_id) AS tickets,
                    SUM(COALESCE(qp.duration_seconds,
                       EXTRACT(EPOCH FROM (COALESCE(qp.exited_at, NOW()) - qp.entered_at))
                    ))::bigint AS wall_seconds,
                    AVG(COALESCE(qp.duration_seconds,
                       EXTRACT(EPOCH FROM (COALESCE(qp.exited_at, NOW()) - qp.entered_at))
                    )) AS mean_seconds,
                    PERCENTILE_CONT(0.9) WITHIN GROUP (
                      ORDER BY COALESCE(qp.duration_seconds,
                       EXTRACT(EPOCH FROM (COALESCE(qp.exited_at, NOW()) - qp.entered_at)))
                    ) AS p90_seconds
                  FROM queue_periods qp
                  WHERE {qp_scope}
                  GROUP BY qp.queue_name
                ),
                no_own AS (
                  SELECT op.queue_name,
                         SUM(CASE WHEN op.owner IS NULL
                                  OR LOWER(op.owner) IN ('root@localhost','otrs admin (root@localhost)','')
                                  THEN EXTRACT(EPOCH FROM (COALESCE(op.end_time, NOW()) - op.start_time))
                                  ELSE 0 END)::bigint AS no_owner_seconds,
                         SUM(EXTRACT(EPOCH FROM (COALESCE(op.end_time, NOW()) - op.start_time)))::bigint AS owned_total
                  FROM ownership_periods op
                  WHERE {op_scope}
                  GROUP BY op.queue_name
                ),
                touches AS (
                  SELECT te.queue_name,
                         COUNT(*) FILTER (WHERE te.is_system_action IS NOT TRUE) AS non_sys_events
                  FROM ticket_events te
                  WHERE {ev_scope}
                  GROUP BY te.queue_name
                ),
                transitions AS (
                  SELECT te.src_queue AS queue_name, te.dest_queue AS target
                  FROM ticket_events te
                  WHERE te.src_queue IS NOT NULL
                    AND te.dest_queue IS NOT NULL
                    AND te.src_queue != te.dest_queue
                    AND {ev_scope}
                ),
                fanout AS (
                  SELECT queue_name,
                         target,
                         COUNT(*) AS n
                  FROM transitions
                  GROUP BY queue_name, target
                ),
                breach_per_q AS (
                  SELECT m.queue_name,
                         COUNT(*) FILTER (WHERE m.sla_breached IS TRUE) AS breaches,
                         COUNT(*) AS total
                  FROM sla_metrics m
                  WHERE m.metric_name IN ('resolution_time','wall_resolution_time')
                    AND {m_scope}
                  GROUP BY m.queue_name
                ),
                re_entries AS (
                  SELECT queue_name,
                         SUM(GREATEST(0, c - 1)) AS reentries,
                         SUM(c) AS total_entries
                  FROM (
                    SELECT queue_name, ticket_id, COUNT(*) AS c
                    FROM queue_periods
                    WHERE {qp_inner_scope}
                    GROUP BY queue_name, ticket_id
                  ) z
                  GROUP BY queue_name
                )
                SELECT
                  q.queue_name AS queue,
                  q.tickets, q.wall_seconds, q.mean_seconds, q.p90_seconds,
                  COALESCE(no_own.no_owner_seconds, 0) AS no_owner_seconds,
                  COALESCE(no_own.owned_total, 0) AS owned_total,
                  COALESCE(touches.non_sys_events, 0) AS non_sys_events,
                  COALESCE(re_entries.reentries, 0) AS reentries,
                  COALESCE(re_entries.total_entries, 0) AS total_entries,
                  COALESCE(breach_per_q.breaches, 0) AS breaches,
                  COALESCE(breach_per_q.total, 0) AS breach_total
                FROM qp_agg q
                LEFT JOIN no_own ON no_own.queue_name = q.queue_name
                LEFT JOIN touches ON touches.queue_name = q.queue_name
                LEFT JOIN re_entries ON re_entries.queue_name = q.queue_name
                LEFT JOIN breach_per_q ON breach_per_q.queue_name = q.queue_name
                ORDER BY q.wall_seconds DESC NULLS LAST
                LIMIT :lim
            """),
            # When filtering is requested, fetch more rows so we don't lose
            # smaller queues that happen to fall below the global cap.
            {
                "lim": max(limit, 500) if queues else limit,
                **_scope_binds(scope),
            },
        ).mappings().all()
        # Restrict to the user's selected queues if a list was passed in.
        if queues:
            wanted = set(queues)
            base = [r for r in base if r["queue"] in wanted]

        # Fanout (entropy) — separate, sized by queue
        fanout_rows = db.execute(
            text(f"""
                SELECT te.src_queue AS queue_name, te.dest_queue AS target, COUNT(*) AS n
                FROM ticket_events te
                WHERE te.src_queue IS NOT NULL
                  AND te.dest_queue IS NOT NULL
                  AND te.src_queue != te.dest_queue
                  AND {ev_scope}
                GROUP BY te.src_queue, te.dest_queue
            """),
            _scope_binds(scope),
        ).mappings().all()
        fanout: dict[str, list[tuple[str, int]]] = {}
        for r in fanout_rows:
            fanout.setdefault(r["queue_name"], []).append((r["target"], int(r["n"])))

        out: list[QueueForensicRow] = []
        for r in base:
            wall = int(r["wall_seconds"] or 0)
            no_own = int(r["no_owner_seconds"] or 0)
            owned_total = int(r["owned_total"] or 0)
            non_sys = int(r["non_sys_events"] or 0)
            re_n = int(r["reentries"] or 0)
            ent_total = int(r["total_entries"] or 0)
            breaches = int(r["breaches"] or 0)
            br_total = int(r["breach_total"] or 0)

            wall_h = wall / 3600.0 if wall else 0.0
            no_own_ratio = (no_own / owned_total) if owned_total > 0 else 0.0
            touch_rate = (non_sys / wall_h) if wall_h > 0 else 0.0
            transfer_loop = (re_n / ent_total) if ent_total > 0 else 0.0
            stagnation = max(0.0, 1.0 - min(1.0, touch_rate / 2.0))   # 2 touches/h → 0 stagnation
            breach_rate = (breaches / br_total) if br_total > 0 else 0.0

            targets = fanout.get(r["queue"], [])
            total_out = sum(n for _, n in targets) or 1
            entropy = 0.0
            for _, n in targets:
                p = n / total_out
                if p > 0:
                    entropy -= p * math.log2(p)
            unique_t = len(targets)
            chaos = (entropy / math.log2(unique_t)) if unique_t > 1 else 0.0

            # parking-lot: high no-owner + low touch-rate + long stay
            mean_s = float(r["mean_seconds"] or 0) / 3600.0
            parking = (
                min(1.0, no_own_ratio)
                * (1.0 - min(1.0, touch_rate / 1.0))
                * min(1.0, mean_s / 24.0)
            )

            # black-hole: parking-lot intensified by breach + low exit rate
            exit_rate = ((ent_total - re_n) / ent_total) if ent_total > 0 else 0.0
            black_hole = parking * (0.5 + 0.5 * breach_rate) * (1.0 - exit_rate * 0.5)

            # pressure = concurrent breaching tickets / capacity proxy (use tickets as proxy)
            pressure = (breaches / max(1, int(r["tickets"] or 1)))

            out.append(QueueForensicRow(
                queue=r["queue"],
                total_tickets=int(r["tickets"] or 0),
                total_wall_hours=round(wall_h, 2),
                mean_stay_hours=round(mean_s, 2),
                p90_stay_hours=round(float(r["p90_seconds"] or 0) / 3600.0, 2),
                no_owner_ratio=round(no_own_ratio, 4),
                touch_rate_per_hour=round(touch_rate, 4),
                entropy_bits=round(entropy, 4),
                unique_targets=unique_t,
                routing_chaos_score=round(chaos, 4),
                parking_lot_score=round(parking, 4),
                black_hole_score=round(black_hole, 4),
                stagnation_score=round(stagnation, 4),
                transfer_loop_score=round(transfer_loop, 4),
                pressure_score=round(pressure, 4),
                breach_count=breaches,
                breach_rate=round(breach_rate, 4),
            ))
        return out

    # ----- Routing transition graph -------------------------------------

    @staticmethod
    def transitions(
        db: Session, limit: int = 200, queues: list[str] | None = None,
        scope: Optional[TimeScope] = None,
    ) -> list[dict[str, Any]]:
        """Routing edges. If `queues` is given, only edges that touch one of
        the selected queues (either as source or destination) are returned —
        useful for "focus on my favorite queues" mode."""
        rows = db.execute(
            text("""
                SELECT src_queue, dest_queue, COUNT(*) AS n,
                       COUNT(DISTINCT ticket_id) AS tickets
                FROM ticket_events
                WHERE src_queue IS NOT NULL AND dest_queue IS NOT NULL
                  AND src_queue != dest_queue
                  AND (:since IS NULL OR event_time >= :since)
                  AND (:until IS NULL OR event_time < :until)
                GROUP BY src_queue, dest_queue
                ORDER BY n DESC
                LIMIT :lim
            """),
            {"lim": max(limit, 1000) if queues else limit, **_scope_binds(scope)},
        ).mappings().all()
        out = [
            {"src": r["src_queue"], "dst": r["dest_queue"],
             "count": int(r["n"]), "tickets": int(r["tickets"])}
            for r in rows
        ]
        if queues:
            qs = set(queues)
            out = [e for e in out if e["src"] in qs or e["dst"] in qs][:limit]
        return out

    # ----- Hot-potato detector ------------------------------------------

    @staticmethod
    def hot_potato_tickets(
        db: Session, min_moves: int = 3, limit: int = 50,
        queues: list[str] | None = None,
        scope: Optional[TimeScope] = None,
    ) -> list[dict[str, Any]]:
        rows = db.execute(
            text("""
                SELECT te.ticket_id,
                       MAX(s.ticket_number) AS ticket_number,
                       MAX(s.current_queue) AS current_queue,
                       MAX(s.current_state) AS current_state,
                       COUNT(*) FILTER (
                         WHERE te.src_queue IS NOT NULL
                           AND te.dest_queue IS NOT NULL
                           AND te.src_queue != te.dest_queue
                       ) AS moves,
                       COUNT(*) FILTER (
                         WHERE te.new_owner IS NOT NULL
                           AND te.old_owner IS NOT NULL
                           AND te.new_owner != te.old_owner
                       ) AS owner_changes,
                       COUNT(DISTINCT te.queue_name) AS distinct_queues
                FROM ticket_events te
                LEFT JOIN ticket_snapshots s ON s.ticket_id = te.ticket_id
                WHERE (:since IS NULL OR te.event_time >= :since)
                  AND (:until IS NULL OR te.event_time < :until)
                GROUP BY te.ticket_id
                HAVING COUNT(*) FILTER (
                  WHERE te.src_queue IS NOT NULL
                    AND te.dest_queue IS NOT NULL
                    AND te.src_queue != te.dest_queue
                ) >= :mn
                AND (
                  (:has_queues IS FALSE)
                  OR EXISTS (
                    SELECT 1 FROM ticket_events te2
                    WHERE te2.ticket_id = te.ticket_id
                      AND te2.queue_name = ANY(:queue_list)
                  )
                )
                ORDER BY moves DESC
                LIMIT :lim
            """),
            {
                "mn": min_moves, "lim": limit,
                "has_queues": bool(queues),
                "queue_list": queues or [],
                **_scope_binds(scope),
            },
        ).mappings().all()
        return [dict(r) for r in rows]
