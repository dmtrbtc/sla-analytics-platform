"""SLA Loss Aggregate Engine — v1.8.

Aggregates per-segment loss across ALL tickets to answer:

  - "Top loss queues":          which queues consume the most resolution
                                budget across the whole portfolio?
  - "Most expensive queues":    same but normalized per ticket
  - "Tickets dying in queue":   currently-open tickets with the largest
                                accumulated resolution loss
  - "No-owner parking lots":    queues holding the most no_owner_minutes

The engine sums seconds at the segment grain to avoid double-counting that
plagues whole-lifecycle loss metrics. The grain is:

   queue_periods × ownership_periods   (joined on ticket + time overlap)

Pure SQL — no per-ticket Python iteration. Filter `queues: list[str]` is
honored everywhere so favorite-queue mode works.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.forensics.time_scope import (
    TimeScope,
    overlap_seconds_sql,
    scope_filter_sql,
    scope_params,
)

logger = logging.getLogger(__name__)


SYS_OWNER_SQL = (
    "(owner IS NULL OR LOWER(owner) IN "
    "('root@localhost','otrs admin (root@localhost)',''))"
)


def _params(queues: Optional[list[str]], scope: Optional[TimeScope] = None) -> dict:
    """Merge queue-filter binds + time-scope binds in one dict for `.execute()`."""
    p = {"has_queues": bool(queues), "queue_list": queues or []}
    if scope is not None:
        p.update(scope_params(scope))
    else:
        p.update({"since": None, "until": None})
    return p


class SLALossEngine:

    # ────────────────────────────────────────────────────────────────────
    # TOP LOSS QUEUES — overlap-aware contribution inside scope window
    # ────────────────────────────────────────────────────────────────────
    @staticmethod
    def top_loss_queues(
        db: Session,
        limit: int = 25,
        queues: Optional[list[str]] = None,
        days: Optional[int] = None,
        scope: Optional[TimeScope] = None,
    ) -> list[dict[str, Any]]:
        """Wall-clock contribution. When `scope` is non-all-time, every
        segment is counted ONLY for the portion that overlaps the window.

        `days` is preserved for backward-compat callers; if `scope` is
        provided it wins.
        """
        # Backward-compat: if old `days` was supplied but no scope, build
        # an implicit scope from it.
        if scope is None and days:
            from app.services.forensics.time_scope import parse_time_scope
            scope = parse_time_scope(period=f"{days}d")
        params = _params(queues, scope)
        # Overlap expressions (active when :since/:until are non-null)
        OV_QP = overlap_seconds_sql("qp.entered_at", "qp.exited_at")
        OV_OP_X = (
            "GREATEST(0, EXTRACT(EPOCH FROM ("
            "LEAST(COALESCE(qp.exited_at, NOW()), COALESCE(op.end_time, NOW()), "
            "COALESCE(:until, COALESCE(qp.exited_at, NOW())))"
            " - "
            "GREATEST(qp.entered_at, op.start_time, COALESCE(:since, qp.entered_at))"
            ")))"
        )
        FILTER_QP = scope_filter_sql("qp.entered_at", "qp.exited_at")
        # owned share — overlap with non-system ownership
        # no-owner share — overlap with system ownership
        rows = db.execute(
            text(f"""
                WITH seg AS (
                  SELECT qp.queue_name,
                         qp.ticket_id,
                         qp.entered_at,
                         COALESCE(qp.exited_at, NOW()) AS exited_at,
                         {OV_QP}::bigint AS wall_sec
                  FROM queue_periods qp
                  WHERE {FILTER_QP}
                    AND ((:has_queues IS FALSE) OR qp.queue_name = ANY(:queue_list))
                ),
                noown AS (
                  SELECT qp.queue_name,
                         SUM({OV_OP_X})::bigint AS no_owner_sec
                  FROM queue_periods qp
                  JOIN ownership_periods op
                    ON op.ticket_id = qp.ticket_id
                  WHERE {SYS_OWNER_SQL.replace('owner','op.owner')}
                    AND ((:has_queues IS FALSE) OR qp.queue_name = ANY(:queue_list))
                  GROUP BY qp.queue_name
                )
                SELECT seg.queue_name,
                       COUNT(*) AS segments,
                       COUNT(DISTINCT seg.ticket_id) AS distinct_tickets,
                       SUM(seg.wall_sec)::bigint AS total_wall_sec,
                       AVG(seg.wall_sec)::bigint AS mean_wall_sec,
                       COALESCE(MAX(noown.no_owner_sec), 0) AS no_owner_sec
                FROM seg
                LEFT JOIN noown USING (queue_name)
                WHERE seg.wall_sec > 0
                GROUP BY seg.queue_name
                ORDER BY total_wall_sec DESC NULLS LAST
                LIMIT :lim
            """),
            {**params, "lim": limit},
        ).mappings().all()

        total_global = sum(int(r["total_wall_sec"] or 0) for r in rows) or 1
        return [
            {
                "queue": r["queue_name"],
                "segments": int(r["segments"]),
                "distinct_tickets": int(r["distinct_tickets"]),
                "total_wall_hours": round(int(r["total_wall_sec"] or 0) / 3600.0, 1),
                "mean_wall_minutes": int(int(r["mean_wall_sec"] or 0) / 60),
                "no_owner_hours": round(int(r["no_owner_sec"] or 0) / 3600.0, 1),
                "share_of_total_pct": round(
                    int(r["total_wall_sec"] or 0) / total_global * 100, 2,
                ),
            }
            for r in rows
        ]

    # ────────────────────────────────────────────────────────────────────
    # MOST EXPENSIVE PER TICKET — normalized cost per ticket
    # ────────────────────────────────────────────────────────────────────
    @staticmethod
    def most_expensive_queues(
        db: Session,
        limit: int = 25,
        queues: Optional[list[str]] = None,
        min_tickets: int = 5,
        scope: Optional[TimeScope] = None,
    ) -> list[dict[str, Any]]:
        OV = overlap_seconds_sql("entered_at", "exited_at")
        FL = scope_filter_sql("entered_at", "exited_at")
        rows = db.execute(
            text(f"""
                SELECT queue_name,
                       COUNT(DISTINCT ticket_id) AS tickets,
                       SUM({OV})::bigint AS total_wall_sec
                FROM queue_periods
                WHERE {FL}
                  AND ((:has_queues IS FALSE) OR queue_name = ANY(:queue_list))
                GROUP BY queue_name
                HAVING COUNT(DISTINCT ticket_id) >= :min_tickets
                   AND SUM({OV}) > 0
                ORDER BY (SUM({OV})::float
                          / NULLIF(COUNT(DISTINCT ticket_id), 0)) DESC NULLS LAST
                LIMIT :lim
            """),
            {**_params(queues, scope), "lim": limit, "min_tickets": min_tickets},
        ).mappings().all()
        return [
            {
                "queue": r["queue_name"],
                "tickets": int(r["tickets"]),
                "total_wall_hours": round(int(r["total_wall_sec"] or 0) / 3600.0, 1),
                "cost_per_ticket_hours": round(
                    int(r["total_wall_sec"] or 0) / max(1, int(r["tickets"])) / 3600.0, 2,
                ),
            }
            for r in rows
        ]

    # ────────────────────────────────────────────────────────────────────
    # TICKETS DYING IN QUEUE — open tickets with high accumulated wall time
    # ────────────────────────────────────────────────────────────────────
    @staticmethod
    def dying_in_queue(
        db: Session,
        limit: int = 25,
        queues: Optional[list[str]] = None,
        scope: Optional[TimeScope] = None,
    ) -> list[dict[str, Any]]:
        OV = overlap_seconds_sql("qp.entered_at", "qp.exited_at")
        FL = scope_filter_sql("qp.entered_at", "qp.exited_at")
        rows = db.execute(
            text(f"""
                SELECT ts.ticket_id,
                       ts.ticket_number,
                       ts.title,
                       ts.current_queue,
                       ts.current_owner,
                       ts.current_state,
                       SUM({OV})::bigint AS total_wall_sec,
                       COUNT(DISTINCT qp.queue_name) AS queues_visited,
                       COUNT(*) AS segments
                FROM ticket_snapshots ts
                JOIN queue_periods qp ON qp.ticket_id = ts.ticket_id
                WHERE ts.is_closed = FALSE
                  AND ts.is_merged = FALSE
                  AND {FL}
                  AND ((:has_queues IS FALSE) OR ts.current_queue = ANY(:queue_list))
                GROUP BY ts.ticket_id, ts.ticket_number, ts.title,
                         ts.current_queue, ts.current_owner, ts.current_state
                HAVING SUM({OV}) > 0
                ORDER BY total_wall_sec DESC NULLS LAST
                LIMIT :lim
            """),
            {**_params(queues, scope), "lim": limit},
        ).mappings().all()
        return [
            {
                "ticket_id": int(r["ticket_id"]),
                "ticket_number": r["ticket_number"],
                "title": r["title"],
                "current_queue": r["current_queue"],
                "current_owner": r["current_owner"],
                "current_state": r["current_state"],
                "total_wall_hours": round(int(r["total_wall_sec"] or 0) / 3600.0, 1),
                "queues_visited": int(r["queues_visited"]),
                "segments": int(r["segments"]),
            }
            for r in rows
        ]

    # ────────────────────────────────────────────────────────────────────
    # NO-OWNER PARKING LOTS — queues holding the most no_owner time
    # ────────────────────────────────────────────────────────────────────
    @staticmethod
    def parking_lots(
        db: Session,
        limit: int = 25,
        queues: Optional[list[str]] = None,
        scope: Optional[TimeScope] = None,
    ) -> list[dict[str, Any]]:
        OV = overlap_seconds_sql("start_time", "end_time")
        FL = scope_filter_sql("start_time", "end_time")
        rows = db.execute(
            text(f"""
                SELECT queue_name,
                       SUM(CASE WHEN {SYS_OWNER_SQL} THEN {OV} ELSE 0 END)::bigint AS no_owner_sec,
                       SUM({OV})::bigint AS total_sec,
                       COUNT(DISTINCT ticket_id) AS distinct_tickets
                FROM ownership_periods
                WHERE {FL}
                  AND ((:has_queues IS FALSE) OR queue_name = ANY(:queue_list))
                GROUP BY queue_name
                HAVING SUM({OV}) > 0
                ORDER BY no_owner_sec DESC NULLS LAST
                LIMIT :lim
            """),
            {**_params(queues, scope), "lim": limit},
        ).mappings().all()
        return [
            {
                "queue": r["queue_name"],
                "no_owner_hours": round(int(r["no_owner_sec"] or 0) / 3600.0, 1),
                "total_owned_hours": round(int(r["total_sec"] or 0) / 3600.0, 1),
                "no_owner_pct": round(
                    int(r["no_owner_sec"] or 0)
                    / max(1, int(r["total_sec"] or 1)) * 100, 2,
                ),
                "distinct_tickets": int(r["distinct_tickets"]),
            }
            for r in rows
        ]

    # ────────────────────────────────────────────────────────────────────
    # SLA-LOSS WATERFALL — single ticket, ordered segments with cumulative
    # ────────────────────────────────────────────────────────────────────
    @staticmethod
    def waterfall(db: Session, ticket_id: int) -> list[dict[str, Any]]:
        rows = db.execute(
            text("""
                SELECT queue_name, entered_at, exited_at,
                       COALESCE(duration_seconds,
                          EXTRACT(EPOCH FROM
                            (COALESCE(exited_at, NOW()) - entered_at)))::bigint
                          AS dur_sec
                FROM queue_periods WHERE ticket_id = :tid
                ORDER BY entered_at
            """),
            {"tid": ticket_id},
        ).mappings().all()
        out = []
        cum = 0
        for r in rows:
            d = int(r["dur_sec"] or 0)
            cum += d
            out.append({
                "queue_name": r["queue_name"],
                "entered_at": r["entered_at"].isoformat() if r["entered_at"] else None,
                "exited_at": r["exited_at"].isoformat() if r["exited_at"] else None,
                "minutes": d // 60,
                "cumulative_minutes": cum // 60,
            })
        return out
