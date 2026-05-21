"""Deep per-queue forensic detail panel.

Single endpoint that returns everything the UI needs to render an
operational queue detail card:
- breach % (V2 active + V3 wall-clock)
- MTTA / MTTR
- avg stagnation
- no-owner %
- routing entropy / unique targets
- reassignment storm count
- top breached owners
- hidden breach delta
- busiest hours
- queue health score (0..100 composite)
- top recent breaches
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import sync_session_factory
from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/{queue_name:path}")
def queue_detail(queue_name: str):
    """Return all forensic + operational metrics for ONE queue."""
    with sync_session_factory() as db:
        # 1. Overall snapshot
        snap = db.execute(text("""
            SELECT
              COUNT(*) FILTER (WHERE current_queue = :q) AS total_tickets,
              COUNT(*) FILTER (WHERE current_queue = :q AND is_closed IS NOT TRUE) AS open_tickets,
              COUNT(*) FILTER (WHERE current_queue = :q AND is_closed IS TRUE) AS closed_tickets
            FROM ticket_snapshots
        """), {"q": queue_name}).mappings().first() or {}

        # 2. SLA metric stats — V2 + V3
        metric_rows = db.execute(text("""
            SELECT metric_name,
                   COUNT(*) AS n,
                   AVG(metric_seconds)::bigint AS avg_sec,
                   SUM(CASE WHEN sla_breached THEN 1 ELSE 0 END) AS breaches,
                   PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY metric_seconds) AS p50,
                   PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY metric_seconds) AS p90
            FROM sla_metrics
            WHERE queue_name = :q
            GROUP BY metric_name
        """), {"q": queue_name}).mappings().all()
        metrics: dict[str, dict] = {}
        for r in metric_rows:
            metrics[r["metric_name"]] = {
                "n": int(r["n"]),
                "avg_seconds": int(r["avg_sec"] or 0),
                "breaches": int(r["breaches"] or 0),
                "p50_seconds": int(r["p50"] or 0),
                "p90_seconds": int(r["p90"] or 0),
            }

        def mn(*names):
            for n in names:
                if n in metrics:
                    return metrics[n]
            return {"n": 0, "avg_seconds": 0, "breaches": 0, "p50_seconds": 0, "p90_seconds": 0}

        resp = mn("first_response_time", "response_time")
        resol = mn("resolution_time")
        wall_resol = mn("wall_resolution_time")
        no_own = mn("no_owner_seconds")
        stag = mn("stagnation_seconds")
        pause = mn("pause_seconds")

        # 3. Queue period stats
        qp = db.execute(text("""
            SELECT
              COUNT(*) AS segments,
              COUNT(DISTINCT ticket_id) AS unique_tickets,
              AVG(COALESCE(duration_seconds,
                  EXTRACT(EPOCH FROM (COALESCE(exited_at, NOW()) - entered_at))))::bigint
                AS mean_stay_sec,
              PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY
                COALESCE(duration_seconds,
                  EXTRACT(EPOCH FROM (COALESCE(exited_at, NOW()) - entered_at)))) AS p90_sec
            FROM queue_periods WHERE queue_name = :q
        """), {"q": queue_name}).mappings().first() or {}

        # 4. Ownership stats
        own = db.execute(text("""
            SELECT
              SUM(EXTRACT(EPOCH FROM (COALESCE(end_time, NOW()) - start_time)))::bigint AS total_owned_sec,
              SUM(CASE WHEN owner IS NULL OR LOWER(owner) IN
                       ('root@localhost','otrs admin (root@localhost)','')
                       THEN EXTRACT(EPOCH FROM (COALESCE(end_time, NOW()) - start_time))
                       ELSE 0 END)::bigint AS no_owner_sec,
              COUNT(DISTINCT owner) FILTER (WHERE owner IS NOT NULL
                       AND LOWER(owner) NOT IN
                       ('root@localhost','otrs admin (root@localhost)','')) AS unique_owners
            FROM ownership_periods WHERE queue_name = :q
        """), {"q": queue_name}).mappings().first() or {}

        # 5. Routing fan-out + entropy
        out_rows = db.execute(text("""
            SELECT dest_queue, COUNT(*) AS n
            FROM ticket_events
            WHERE src_queue = :q AND dest_queue IS NOT NULL AND dest_queue != src_queue
            GROUP BY dest_queue
            ORDER BY n DESC
        """), {"q": queue_name}).mappings().all()
        total_out = sum(int(r["n"]) for r in out_rows) or 0
        import math
        entropy_bits = 0.0
        for r in out_rows:
            p = int(r["n"]) / total_out if total_out else 0
            if p > 0:
                entropy_bits -= p * math.log2(p)
        top_targets = [{"queue": r["dest_queue"], "count": int(r["n"])} for r in out_rows[:8]]

        in_rows = db.execute(text("""
            SELECT src_queue, COUNT(*) AS n
            FROM ticket_events
            WHERE dest_queue = :q AND src_queue IS NOT NULL AND src_queue != dest_queue
            GROUP BY src_queue
            ORDER BY n DESC LIMIT 8
        """), {"q": queue_name}).mappings().all()
        top_sources = [{"queue": r["src_queue"], "count": int(r["n"])} for r in in_rows]

        # 6. Top breached owners in this queue
        top_owners = db.execute(text("""
            SELECT owner, COUNT(*) AS breaches
            FROM sla_metrics
            WHERE queue_name = :q AND sla_breached = TRUE
              AND owner IS NOT NULL
              AND LOWER(owner) NOT IN ('root@localhost','otrs admin (root@localhost)','')
            GROUP BY owner ORDER BY breaches DESC LIMIT 10
        """), {"q": queue_name}).mappings().all()

        # 7. Reassignment storms in this queue
        reassigns = db.execute(text("""
            SELECT COUNT(*) FROM ticket_events
            WHERE queue_name = :q
              AND new_owner IS NOT NULL AND old_owner IS NOT NULL
              AND new_owner != old_owner
        """), {"q": queue_name}).scalar() or 0

        # 8. Busiest hours (by event_time hour-of-day)
        busiest = db.execute(text("""
            SELECT EXTRACT(HOUR FROM event_time)::int AS hour, COUNT(*) AS n
            FROM ticket_events
            WHERE queue_name = :q AND (is_system_action IS NOT TRUE)
            GROUP BY hour ORDER BY hour
        """), {"q": queue_name}).mappings().all()

        # 9. Recent breached tickets (active-time view)
        recent_breaches = db.execute(text("""
            SELECT ticket_id, metric_name, metric_seconds, owner, computed_at
            FROM sla_metrics
            WHERE queue_name = :q AND sla_breached = TRUE
              AND metric_name IN ('first_response_time','response_time','resolution_time')
            ORDER BY computed_at DESC LIMIT 15
        """), {"q": queue_name}).mappings().all()

        # 10. Composite health score (0=worst, 100=best)
        mean_stay_h = float(qp.get("mean_stay_sec") or 0) / 3600.0
        no_owner_ratio = (float(own.get("no_owner_sec") or 0)
                          / (float(own.get("total_owned_sec") or 1) or 1))
        resol_breach_rate = (resol["breaches"] / resol["n"]) if resol["n"] > 0 else 0.0
        wall_breach_rate = (wall_resol["breaches"] / wall_resol["n"]) if wall_resol["n"] > 0 else 0.0
        # Higher score = healthier
        health = 100 * (
            0.35 * (1 - min(1.0, max(wall_breach_rate, resol_breach_rate)))
            + 0.25 * (1 - min(1.0, no_owner_ratio))
            + 0.20 * (1 - min(1.0, mean_stay_h / 72))   # 72h = bad
            + 0.10 * (1 - min(1.0, entropy_bits / 4))    # 4 bits = chaotic
            + 0.10 * (1 - min(1.0, reassigns / max(1, int(qp.get("unique_tickets") or 1))))
        )
        # Hidden breach delta — V3 wall-clock breaches above V2 active-time breaches
        hidden_breach_delta = max(0, wall_resol["breaches"] - resol["breaches"])

    return {
        "queue_name": queue_name,
        "snapshot": dict(snap),
        "metrics": metrics,
        "mtta_seconds": resp["avg_seconds"],
        "mttr_seconds": resol["avg_seconds"],
        "queue_period_stats": {
            "segments": int(qp.get("segments") or 0),
            "unique_tickets": int(qp.get("unique_tickets") or 0),
            "mean_stay_seconds": int(qp.get("mean_stay_sec") or 0),
            "p90_stay_seconds": int(qp.get("p90_sec") or 0),
        },
        "ownership": {
            "total_owned_seconds": int(own.get("total_owned_sec") or 0),
            "no_owner_seconds": int(own.get("no_owner_sec") or 0),
            "no_owner_ratio": round(no_owner_ratio, 4),
            "unique_owners": int(own.get("unique_owners") or 0),
        },
        "routing": {
            "out_total": total_out,
            "out_unique_targets": len(out_rows),
            "entropy_bits": round(entropy_bits, 4),
            "top_destinations": top_targets,
            "top_sources": top_sources,
        },
        "reassignments_total": int(reassigns),
        "top_breach_owners": [dict(r) for r in top_owners],
        "busiest_hours": [dict(r) for r in busiest],
        "recent_breaches": [
            {**dict(r), "computed_at": r["computed_at"].isoformat() if r.get("computed_at") else None}
            for r in recent_breaches
        ],
        "stagnation_avg_seconds": stag["avg_seconds"],
        "pause_avg_seconds": pause["avg_seconds"],
        "hidden_breach_delta": hidden_breach_delta,
        "health_score": round(max(0.0, min(100.0, health)), 1),
    }
