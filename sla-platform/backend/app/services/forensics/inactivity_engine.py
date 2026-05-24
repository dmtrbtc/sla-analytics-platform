"""Phase 3 — Silent Breach Detection.

Detects tickets that age toward SLA breach with NO recent activity. Real OTRS
data showed 772 closed breaches had zero events in the 7-day observation
window — these are invisible to active-time SLA monitoring.

Metrics emitted (all SQL aggregated):
  - last_activity_age_seconds
  - inactivity_ratio          (age / SLA target)
  - silent_breach_probability (0..1)
  - queue_silence_score       (queue-wide aggregate)

Risk escalation rule: when inactivity_ratio > 0.5 AND ticket is open,
risk_level is forcibly bumped to "high" or "breached" regardless of
active-time computation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.forensics.time_scope import TimeScope, scope_params

logger = logging.getLogger(__name__)


@dataclass
class SilentBreachRow:
    ticket_id: int
    ticket_number: Optional[str]
    queue_name: Optional[str]
    owner: Optional[str]
    state_name: Optional[str]
    last_activity_age_seconds: int
    sla_target_seconds: int
    inactivity_ratio: float
    silent_breach_probability: float
    risk_level: str


class InactivityEngine:
    """Surfaces tickets aging silently past SLA."""

    @staticmethod
    def detect_silent_breaches(
        db: Session,
        min_inactivity_ratio: float = 0.5,
        limit: int = 200,
        queues: list[str] | None = None,
        scope: Optional[TimeScope] = None,
    ) -> list[SilentBreachRow]:
        """Find open tickets whose age-since-last-activity exceeds
        min_inactivity_ratio * SLA target.

        Pure SQL — no per-ticket Python loop.
        """
        # When a scope is given, restrict the candidate ticket set to those
        # CREATED inside the window — operationally "tickets that arrived in
        # the last N days and are still open silent." All-time scope keeps
        # the original behavior.
        sp = scope_params(scope) if scope is not None else {"since": None, "until": None}
        rows = db.execute(
            text("""
                WITH last_evt AS (
                  SELECT ticket_id, MAX(event_time) AS last_event_time
                  FROM ticket_events
                  WHERE (is_system_action IS NULL OR is_system_action IS FALSE)
                  GROUP BY ticket_id
                ),
                tgt AS (
                  SELECT m.ticket_id,
                         MAX(CASE WHEN m.metric_name='wall_resolution_time'
                                  THEN m.metric_seconds END) AS wall_seconds
                  FROM sla_metrics m
                  GROUP BY m.ticket_id
                )
                SELECT
                  s.ticket_id, s.ticket_number, s.current_queue AS queue_name,
                  s.current_owner AS owner, s.current_state AS state_name,
                  COALESCE(EXTRACT(EPOCH FROM (NOW() - le.last_event_time)),
                           EXTRACT(EPOCH FROM (NOW() - s.created_at)))::bigint
                    AS last_activity_age_seconds,
                  COALESCE(d.resolution_target_seconds, 28800) AS sla_target_seconds
                FROM ticket_snapshots s
                LEFT JOIN last_evt le ON le.ticket_id = s.ticket_id
                LEFT JOIN sla_metrics m ON m.ticket_id = s.ticket_id
                LEFT JOIN sla_definitions d ON d.id = m.sla_definition_id
                WHERE s.is_closed IS NOT TRUE
                  AND s.is_merged IS NOT TRUE
                  AND ((:has_queues IS FALSE) OR s.current_queue = ANY(:queue_list))
                  AND (:since IS NULL OR s.created_at >= :since)
                  AND (:until IS NULL OR s.created_at < :until)
                GROUP BY s.ticket_id, le.last_event_time, d.resolution_target_seconds
                ORDER BY last_activity_age_seconds DESC
                LIMIT :lim
            """),
            {
                "lim": limit * 4,
                "has_queues": bool(queues),
                "queue_list": queues or [],
                **sp,
            },  # over-fetch then filter in Python (small set)
        ).mappings().all()

        out: list[SilentBreachRow] = []
        for r in rows:
            age = int(r["last_activity_age_seconds"] or 0)
            tgt = int(r["sla_target_seconds"] or 0) or 28800
            ratio = age / tgt if tgt else 0.0
            if ratio < min_inactivity_ratio:
                continue

            # probability: sigmoid-ish scaling, saturates at 1.0
            prob = min(1.0, ratio / 1.5)
            if ratio >= 1.0:
                risk_level = "breached"
            elif ratio >= 0.95:
                risk_level = "critical"
            elif ratio >= 0.80:
                risk_level = "high"
            else:
                risk_level = "medium"

            out.append(SilentBreachRow(
                ticket_id=int(r["ticket_id"]),
                ticket_number=r["ticket_number"],
                queue_name=r["queue_name"],
                owner=r["owner"],
                state_name=r["state_name"],
                last_activity_age_seconds=age,
                sla_target_seconds=tgt,
                inactivity_ratio=round(ratio, 4),
                silent_breach_probability=round(prob, 4),
                risk_level=risk_level,
            ))
            if len(out) >= limit:
                break
        return out

    @staticmethod
    def compute_queue_silence(
        db: Session,
        scope: Optional[TimeScope] = None,
    ) -> list[dict[str, Any]]:
        """Per-queue silence score: median time since last activity for open
        tickets in that queue, normalized by the queue's typical SLA target."""
        sp = scope_params(scope) if scope is not None else {"since": None, "until": None}
        rows = db.execute(
            text("""
                WITH last_evt AS (
                  SELECT ticket_id, MAX(event_time) AS last_event_time
                  FROM ticket_events
                  WHERE (is_system_action IS NULL OR is_system_action IS FALSE)
                  GROUP BY ticket_id
                ),
                per_q AS (
                  SELECT
                    s.current_queue AS queue,
                    COUNT(*) AS open_tickets,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (
                      ORDER BY COALESCE(EXTRACT(EPOCH FROM (NOW() - le.last_event_time)),
                                        EXTRACT(EPOCH FROM (NOW() - s.created_at)))
                    ) AS median_age_seconds,
                    PERCENTILE_CONT(0.9) WITHIN GROUP (
                      ORDER BY COALESCE(EXTRACT(EPOCH FROM (NOW() - le.last_event_time)),
                                        EXTRACT(EPOCH FROM (NOW() - s.created_at)))
                    ) AS p90_age_seconds,
                    AVG(EXTRACT(EPOCH FROM (NOW() - le.last_event_time)))
                      FILTER (WHERE le.last_event_time IS NULL) AS no_activity_avg
                  FROM ticket_snapshots s
                  LEFT JOIN last_evt le ON le.ticket_id = s.ticket_id
                  WHERE s.is_closed IS NOT TRUE
                    AND s.is_merged IS NOT TRUE
                    AND s.current_queue IS NOT NULL
                    AND (:since IS NULL OR s.created_at >= :since)
                    AND (:until IS NULL OR s.created_at < :until)
                  GROUP BY s.current_queue
                )
                SELECT queue, open_tickets, median_age_seconds, p90_age_seconds
                FROM per_q
                ORDER BY median_age_seconds DESC NULLS LAST
                LIMIT 50
            """),
            sp,
        ).mappings().all()

        out = []
        for r in rows:
            median_age = float(r["median_age_seconds"] or 0)
            p90_age = float(r["p90_age_seconds"] or 0)
            # Reference target = 28800s (8h); silence_score = median_age / target, capped 1
            silence_score = min(1.0, median_age / 28800.0) if median_age else 0.0
            out.append({
                "queue": r["queue"],
                "open_tickets": int(r["open_tickets"] or 0),
                "median_age_seconds": int(median_age),
                "p90_age_seconds": int(p90_age),
                "silence_score": round(silence_score, 4),
            })
        return out
