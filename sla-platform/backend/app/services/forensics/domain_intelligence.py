"""Domain-specific operations intelligence — v1.6.

Built around the four real OTRS queue families observed in D:\\SLA_test:
  ServiceDesk     — routing hub (1 queue, 255 tickets, 87 open)
  AssetManagement — long-lifecycle (5 queues, 161 tickets, mean stay 35-63h)
  Workplace       — engineer-driven support (4 queues, 134 tickets, breaches)
  Multimedia      — small but event-sensitive (3 queues, 26 tickets)

Each domain answers different operational questions. All SQL — no ORM
N+1 traversals.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ─── Domain glob patterns ────────────────────────────────────────────────
DOMAIN_PATTERNS: dict[str, str] = {
    # SQL LIKE patterns. Escape via ILIKE since real names are mixed case.
    "servicedesk":     "%servicedesk%",
    "assetmanagement": "%asset%",   # AssetManagement, AssetManagement_L2, etc.
    "workplace":       "%workplace%",
    "multimedia":      "%multimedia%",
}


class DomainIntelligence:

    # ────────────────────────────────────────────────────────────────────
    # SHARED — domain inventory
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def _queues_in_domain(db: Session, like: str) -> list[str]:
        rows = db.execute(
            text("""
                SELECT DISTINCT current_queue FROM ticket_snapshots
                WHERE current_queue ILIKE :p
                  AND current_queue IS NOT NULL
                ORDER BY current_queue
            """),
            {"p": like},
        ).scalars().all()
        return list(rows)

    @staticmethod
    def _ticket_counts(db: Session, queues: list[str]) -> dict[str, Any]:
        if not queues:
            return {"total": 0, "open": 0, "closed": 0, "by_queue": []}
        rows = db.execute(
            text("""
                SELECT current_queue,
                       COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE is_closed = FALSE) AS open,
                       COUNT(*) FILTER (WHERE is_closed = TRUE)  AS closed
                FROM ticket_snapshots
                WHERE current_queue = ANY(:q)
                GROUP BY current_queue
                ORDER BY total DESC
            """),
            {"q": queues},
        ).mappings().all()
        total = sum(int(r["total"]) for r in rows)
        open_n = sum(int(r["open"]) for r in rows)
        return {
            "total": total, "open": open_n, "closed": total - open_n,
            "by_queue": [dict(r) for r in rows],
        }

    # ────────────────────────────────────────────────────────────────────
    # 1.  SERVICE DESK — routing hub intelligence
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def servicedesk(db: Session) -> dict[str, Any]:
        """Routing map + transfer forensics + routing-quality scores."""
        queues = DomainIntelligence._queues_in_domain(db, DOMAIN_PATTERNS["servicedesk"])

        counts = DomainIntelligence._ticket_counts(db, queues)

        # Outbound transitions (where ServiceDesk sends tickets)
        outbound = db.execute(
            text("""
                SELECT src_queue, dest_queue,
                       COUNT(*) AS n,
                       COUNT(DISTINCT ticket_id) AS tickets,
                       AVG(EXTRACT(EPOCH FROM (event_time -
                           (SELECT MIN(e2.event_time) FROM ticket_events e2
                            WHERE e2.ticket_id = ticket_events.ticket_id
                              AND e2.queue_name = src_queue
                              AND e2.event_time <= ticket_events.event_time)
                       )))::bigint AS avg_wait_before_transfer_sec
                FROM ticket_events
                WHERE src_queue = ANY(:q)
                  AND dest_queue IS NOT NULL
                  AND dest_queue != src_queue
                GROUP BY src_queue, dest_queue
                ORDER BY n DESC
                LIMIT 25
            """),
            {"q": queues},
        ).mappings().all()

        # Inbound (where tickets come BACK to ServiceDesk — bounce signal)
        inbound = db.execute(
            text("""
                SELECT src_queue, dest_queue, COUNT(*) AS n,
                       COUNT(DISTINCT ticket_id) AS tickets
                FROM ticket_events
                WHERE dest_queue = ANY(:q)
                  AND src_queue IS NOT NULL
                  AND src_queue != dest_queue
                GROUP BY src_queue, dest_queue
                ORDER BY n DESC
                LIMIT 15
            """),
            {"q": queues},
        ).mappings().all()

        # Routing loops: tickets that returned to a ServiceDesk queue ≥2x
        loops = db.execute(
            text("""
                SELECT ticket_id, queue_name, COUNT(*) AS visits
                FROM queue_periods
                WHERE queue_name = ANY(:q)
                GROUP BY ticket_id, queue_name
                HAVING COUNT(*) >= 2
                ORDER BY visits DESC LIMIT 10
            """),
            {"q": queues},
        ).mappings().all()

        # Ownership acquisition latency: creation → first non-system owner
        acq = db.execute(
            text("""
                WITH first_real_owner AS (
                  SELECT op.ticket_id, MIN(op.start_time) AS first_real_at
                  FROM ownership_periods op
                  WHERE LOWER(op.owner) NOT IN
                        ('root@localhost','otrs admin (root@localhost)','')
                    AND op.owner IS NOT NULL
                    AND op.queue_name = ANY(:q)
                  GROUP BY op.ticket_id
                )
                SELECT COUNT(*) AS tickets_with_real_owner,
                       ROUND(AVG(EXTRACT(EPOCH FROM
                         (frbo.first_real_at - ts.created_at)) / 3600.0)::numeric, 2)
                         AS avg_acquisition_hours,
                       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (
                         ORDER BY EXTRACT(EPOCH FROM
                                  (frbo.first_real_at - ts.created_at)) / 3600.0
                       )::numeric, 2) AS median_acquisition_hours,
                       ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (
                         ORDER BY EXTRACT(EPOCH FROM
                                  (frbo.first_real_at - ts.created_at)) / 3600.0
                       )::numeric, 2) AS p90_acquisition_hours
                FROM first_real_owner frbo
                JOIN ticket_snapshots ts ON ts.ticket_id = frbo.ticket_id
                WHERE ts.created_at IS NOT NULL
            """),
            {"q": queues},
        ).mappings().first() or {}

        # Tickets that NEVER got a real owner while in a ServiceDesk queue
        never_owned = db.execute(
            text("""
                SELECT COUNT(DISTINCT op.ticket_id) FROM ownership_periods op
                WHERE op.queue_name = ANY(:q)
                  AND op.ticket_id NOT IN (
                      SELECT op2.ticket_id FROM ownership_periods op2
                      WHERE op2.queue_name = ANY(:q)
                        AND LOWER(op2.owner) NOT IN
                            ('root@localhost','otrs admin (root@localhost)','')
                        AND op2.owner IS NOT NULL
                  )
            """),
            {"q": queues},
        ).scalar() or 0

        # Routing quality score: 100 = clean, 0 = chaos
        # weighted blend of:
        #   bounce factor (re-entries / total entries)
        #   loop ratio (tickets with >=2 visits)
        #   ownership-never-acquired %
        total_entries = db.execute(
            text("SELECT COUNT(*) FROM queue_periods WHERE queue_name = ANY(:q)"),
            {"q": queues},
        ).scalar() or 0
        re_entries = db.execute(
            text("""
                SELECT COALESCE(SUM(GREATEST(visits - 1, 0)), 0) FROM (
                  SELECT COUNT(*) AS visits FROM queue_periods
                  WHERE queue_name = ANY(:q)
                  GROUP BY ticket_id
                ) x
            """),
            {"q": queues},
        ).scalar() or 0
        # Coerce Postgres Decimal/Numeric outputs to plain float so the
        # composite-score arithmetic stays in pure Python floats.
        bounce_factor = float(re_entries or 0) / float(total_entries) if total_entries else 0.0

        tickets_total = max(int(counts["total"]), 1)
        loop_ratio = float(len(loops)) / tickets_total
        never_owned_ratio = float(int(never_owned)) / tickets_total

        routing_quality_score = round(
            100.0 * (1.0 - 0.5 * min(1.0, bounce_factor)
                          - 0.3 * min(1.0, loop_ratio)
                          - 0.2 * min(1.0, never_owned_ratio)),
            2,
        )

        return {
            "domain": "servicedesk",
            "queues": queues,
            "queue_count": len(queues),
            "ticket_counts": counts,
            "outbound_transitions": [
                {**dict(r),
                 "avg_wait_before_transfer_sec":
                     int(r["avg_wait_before_transfer_sec"] or 0)}
                for r in outbound
            ],
            "inbound_transitions": [dict(r) for r in inbound],
            "routing_loops": [dict(r) for r in loops],
            "ownership_acquisition": dict(acq),
            "tickets_never_owned": int(never_owned),
            "tickets_never_owned_pct": round(never_owned_ratio * 100, 1),
            "routing_quality_score": routing_quality_score,
            "bounce_factor": round(bounce_factor, 4),
        }

    # ────────────────────────────────────────────────────────────────────
    # 2.  ASSET MANAGEMENT — long-lifecycle intelligence
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def assetmanagement(db: Session) -> dict[str, Any]:
        """Logistics/warehouse aging + dormant tickets + approval bottlenecks."""
        queues = DomainIntelligence._queues_in_domain(db, DOMAIN_PATTERNS["assetmanagement"])
        counts = DomainIntelligence._ticket_counts(db, queues)

        # Per-queue lifecycle stats
        per_queue = db.execute(
            text("""
                WITH qp_agg AS (
                  SELECT qp.queue_name,
                         COUNT(DISTINCT qp.ticket_id) AS tickets_touching,
                         ROUND(AVG(EXTRACT(EPOCH FROM
                           (COALESCE(qp.exited_at, NOW()) - qp.entered_at)))/3600, 1)
                           AS mean_stay_hours,
                         ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (
                           ORDER BY EXTRACT(EPOCH FROM
                                  (COALESCE(qp.exited_at, NOW()) - qp.entered_at))/3600
                         )::numeric, 1) AS p90_stay_hours
                  FROM queue_periods qp
                  WHERE qp.queue_name = ANY(:q)
                  GROUP BY qp.queue_name
                ),
                no_own AS (
                  SELECT queue_name,
                         ROUND(100.0 * SUM(CASE WHEN owner IS NULL
                           OR LOWER(owner) IN ('root@localhost','otrs admin (root@localhost)','')
                           THEN EXTRACT(EPOCH FROM (COALESCE(end_time, NOW()) - start_time))
                           ELSE 0 END)
                           / NULLIF(SUM(EXTRACT(EPOCH FROM
                                (COALESCE(end_time, NOW()) - start_time))), 0), 1)
                         AS no_owner_pct
                  FROM ownership_periods
                  WHERE queue_name = ANY(:q)
                  GROUP BY queue_name
                ),
                breach AS (
                  SELECT queue_name,
                         COUNT(*) FILTER (WHERE sla_breached AND metric_name='resolution_time') AS resol_breaches,
                         COUNT(*) FILTER (WHERE metric_name='resolution_time') AS resol_metrics
                  FROM sla_metrics
                  WHERE queue_name = ANY(:q)
                  GROUP BY queue_name
                )
                SELECT qp_agg.queue_name,
                       qp_agg.tickets_touching,
                       qp_agg.mean_stay_hours,
                       qp_agg.p90_stay_hours,
                       COALESCE(no_own.no_owner_pct, 0) AS no_owner_pct,
                       COALESCE(breach.resol_breaches, 0) AS resol_breaches,
                       COALESCE(breach.resol_metrics, 0)  AS resol_metrics
                FROM qp_agg
                LEFT JOIN no_own  USING (queue_name)
                LEFT JOIN breach  USING (queue_name)
                ORDER BY qp_agg.tickets_touching DESC
            """),
            {"q": queues},
        ).mappings().all()

        # Dormant open tickets: no events in last 30 days but still open
        dormant = db.execute(
            text("""
                WITH last_evt AS (
                  SELECT ticket_id, MAX(event_time) AS last_at
                  FROM ticket_events
                  WHERE (is_system_action IS NULL OR is_system_action IS FALSE)
                  GROUP BY ticket_id
                )
                SELECT ts.ticket_id, ts.ticket_number, ts.current_queue,
                       ts.current_owner, ts.current_state,
                       ROUND(EXTRACT(EPOCH FROM (NOW() - COALESCE(le.last_at, ts.created_at)))/86400.0, 1)
                         AS dormant_days
                FROM ticket_snapshots ts
                LEFT JOIN last_evt le ON le.ticket_id = ts.ticket_id
                WHERE ts.current_queue = ANY(:q)
                  AND ts.is_closed = FALSE
                  AND (le.last_at IS NULL
                       OR le.last_at < NOW() - INTERVAL '30 days')
                ORDER BY dormant_days DESC
                LIMIT 30
            """),
            {"q": queues},
        ).mappings().all()

        # Reopen frequency
        reopens = db.execute(
            text("""
                SELECT COUNT(*) AS reopen_events,
                       COUNT(DISTINCT ticket_id) AS distinct_reopened
                FROM ticket_events
                WHERE queue_name = ANY(:q)
                  AND LOWER(event_type) LIKE '%reopen%'
            """),
            {"q": queues},
        ).mappings().first() or {}

        # Pending-state proxy (tickets that hold a pending state in scope)
        pending_states = db.execute(
            text("""
                SELECT state_name, COUNT(*) AS hits
                FROM ticket_events
                WHERE queue_name = ANY(:q)
                  AND state_name ILIKE 'pending%'
                GROUP BY state_name ORDER BY hits DESC LIMIT 6
            """),
            {"q": queues},
        ).mappings().all()

        return {
            "domain": "assetmanagement",
            "queues": queues,
            "queue_count": len(queues),
            "ticket_counts": counts,
            "per_queue_pathology": [dict(r) for r in per_queue],
            "dormant_open_tickets": [
                {**dict(r), "dormant_days": float(r["dormant_days"] or 0)}
                for r in dormant
            ],
            "dormant_count": len(dormant),
            "reopen_stats": dict(reopens),
            "pending_state_hits": [dict(r) for r in pending_states],
        }

    # ────────────────────────────────────────────────────────────────────
    # 3.  WORKPLACE — engineer overload + site hotspots
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def workplace(db: Session) -> dict[str, Any]:
        """Engineer overload + site hotspots + MTTA/MTTR per site."""
        queues = DomainIntelligence._queues_in_domain(db, DOMAIN_PATTERNS["workplace"])
        counts = DomainIntelligence._ticket_counts(db, queues)

        # Top engineers (by tickets & hours owned)
        engineers = db.execute(
            text("""
                SELECT owner,
                       COUNT(DISTINCT ticket_id) AS tickets_held,
                       ROUND(SUM(EXTRACT(EPOCH FROM
                         (COALESCE(end_time, NOW()) - start_time)))/3600, 1)
                         AS hours_owned
                FROM ownership_periods
                WHERE queue_name = ANY(:q)
                  AND owner IS NOT NULL
                  AND LOWER(owner) NOT IN
                      ('root@localhost','otrs admin (root@localhost)','')
                GROUP BY owner
                ORDER BY tickets_held DESC LIMIT 15
            """),
            {"q": queues},
        ).mappings().all()

        # Site = derive from queue suffix (e.g. -Veshki, -Plaza, -Esipovo)
        sites = db.execute(
            text("""
                SELECT
                  CASE
                    WHEN current_queue ILIKE '%veshki%'  THEN 'Veshki'
                    WHEN current_queue ILIKE '%plaza%'   THEN 'Plaza'
                    WHEN current_queue ILIKE '%esipovo%' THEN 'Esipovo'
                    ELSE 'Other'
                  END AS site,
                  COUNT(*) AS tickets,
                  COUNT(*) FILTER (WHERE is_closed=FALSE) AS open_now
                FROM ticket_snapshots
                WHERE current_queue = ANY(:q)
                GROUP BY site ORDER BY tickets DESC
            """),
            {"q": queues},
        ).mappings().all()

        # Per-site MTTA / MTTR via metric_seconds aggregation
        site_metrics = db.execute(
            text("""
                WITH t AS (
                  SELECT m.ticket_id, m.metric_name, m.metric_seconds, m.sla_breached,
                         CASE
                           WHEN m.queue_name ILIKE '%veshki%'  THEN 'Veshki'
                           WHEN m.queue_name ILIKE '%plaza%'   THEN 'Plaza'
                           WHEN m.queue_name ILIKE '%esipovo%' THEN 'Esipovo'
                           ELSE 'Other'
                         END AS site
                  FROM sla_metrics m
                  WHERE m.queue_name = ANY(:q)
                )
                SELECT site,
                       ROUND(AVG(metric_seconds) FILTER (WHERE metric_name IN ('first_response_time','response_time'))) AS mtta_seconds,
                       ROUND(AVG(metric_seconds) FILTER (WHERE metric_name = 'resolution_time')) AS mttr_seconds,
                       COUNT(*) FILTER (WHERE sla_breached AND metric_name='resolution_time') AS breaches
                FROM t
                GROUP BY site ORDER BY mttr_seconds DESC NULLS LAST
            """),
            {"q": queues},
        ).mappings().all()

        # Repeat-customer detection
        repeat_customers = db.execute(
            text("""
                SELECT customer_id, COUNT(*) AS tickets
                FROM ticket_snapshots
                WHERE current_queue = ANY(:q)
                  AND customer_id IS NOT NULL
                GROUP BY customer_id
                HAVING COUNT(*) >= 3
                ORDER BY tickets DESC LIMIT 15
            """),
            {"q": queues},
        ).mappings().all()

        # Overload indicator: engineer hours_owned / 160 (one month FTE)
        overloaded = [
            {
                **dict(e),
                "overload_ratio": round(float(e["hours_owned"] or 0) / 160.0, 2),
            }
            for e in engineers
        ]
        # Mark anyone above 2× monthly FTE-equivalent as overloaded
        overload_count = sum(1 for e in overloaded if e["overload_ratio"] >= 2.0)

        return {
            "domain": "workplace",
            "queues": queues,
            "queue_count": len(queues),
            "ticket_counts": counts,
            "engineers": overloaded,
            "overloaded_engineer_count": overload_count,
            "sites": [dict(r) for r in sites],
            "site_metrics": [dict(r) for r in site_metrics],
            "repeat_customers": [dict(r) for r in repeat_customers],
        }

    # ────────────────────────────────────────────────────────────────────
    # 4.  MULTIMEDIA — event-driven, low-volume but spiky
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def multimedia(db: Session) -> dict[str, Any]:
        """Event-window analytics + criticality detection."""
        queues = DomainIntelligence._queues_in_domain(db, DOMAIN_PATTERNS["multimedia"])
        counts = DomainIntelligence._ticket_counts(db, queues)

        # Hour-of-day creation distribution — find the business-hours sensitivity
        hour_dist = db.execute(
            text("""
                SELECT EXTRACT(HOUR FROM created_at)::int AS hour,
                       COUNT(*) AS tickets
                FROM ticket_snapshots
                WHERE current_queue = ANY(:q)
                  AND created_at IS NOT NULL
                GROUP BY hour ORDER BY hour
            """),
            {"q": queues},
        ).mappings().all()

        # Day-of-week
        dow_dist = db.execute(
            text("""
                SELECT EXTRACT(ISODOW FROM created_at)::int AS dow,
                       COUNT(*) AS tickets
                FROM ticket_snapshots
                WHERE current_queue = ANY(:q)
                  AND created_at IS NOT NULL
                GROUP BY dow ORDER BY dow
            """),
            {"q": queues},
        ).mappings().all()

        # Per-queue volume + age
        per_queue = db.execute(
            text("""
                SELECT current_queue,
                       COUNT(*) AS tickets,
                       COUNT(*) FILTER (WHERE is_closed=FALSE) AS open_now,
                       ROUND(AVG(EXTRACT(EPOCH FROM
                          (COALESCE(resolution_at, NOW()) - created_at))/3600), 1)
                         AS avg_lifetime_hours
                FROM ticket_snapshots
                WHERE current_queue = ANY(:q)
                GROUP BY current_queue ORDER BY tickets DESC
            """),
            {"q": queues},
        ).mappings().all()

        # Title text scan for criticality markers (VIP, executive, urgent, etc.)
        markers = db.execute(
            text("""
                SELECT ticket_number, current_queue, title,
                       is_closed, created_at
                FROM ticket_snapshots
                WHERE current_queue = ANY(:q)
                  AND (LOWER(title) LIKE '%vip%'
                       OR LOWER(title) LIKE '%executive%'
                       OR LOWER(title) LIKE '%директор%'
                       OR LOWER(title) LIKE '%президент%'
                       OR LOWER(title) LIKE '%срочн%'
                       OR LOWER(title) LIKE '%urgent%'
                       OR LOWER(title) LIKE '%переговор%')
                ORDER BY created_at DESC LIMIT 20
            """),
            {"q": queues},
        ).mappings().all()

        # SLA breach counts (small dataset)
        breach_row = db.execute(
            text("""
                SELECT
                  COUNT(*) FILTER (WHERE sla_breached AND metric_name='resolution_time') AS resol_breaches,
                  COUNT(*) FILTER (WHERE metric_name='resolution_time') AS resol_metrics
                FROM sla_metrics WHERE queue_name = ANY(:q)
            """),
            {"q": queues},
        ).mappings().first() or {}

        # Repeat infrastructure failures (same customer, multiple Multimedia tickets)
        infra_instability = db.execute(
            text("""
                SELECT customer_id, COUNT(*) AS hits,
                       COUNT(DISTINCT current_queue) AS distinct_queues
                FROM ticket_snapshots
                WHERE current_queue = ANY(:q)
                  AND customer_id IS NOT NULL
                GROUP BY customer_id HAVING COUNT(*) >= 2
                ORDER BY hits DESC LIMIT 10
            """),
            {"q": queues},
        ).mappings().all()

        return {
            "domain": "multimedia",
            "queues": queues,
            "queue_count": len(queues),
            "ticket_counts": counts,
            "per_queue": [dict(r) for r in per_queue],
            "hour_distribution": [dict(r) for r in hour_dist],
            "dow_distribution": [dict(r) for r in dow_dist],
            "criticality_markers": [
                {**dict(r),
                 "created_at": r["created_at"].isoformat() if r["created_at"] else None}
                for r in markers
            ],
            "criticality_count": len(markers),
            "breach_stats": dict(breach_row),
            "infra_instability_customers": [dict(r) for r in infra_instability],
        }
