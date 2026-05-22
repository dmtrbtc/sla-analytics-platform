"""Operational Review System — v2.0.

Three endpoints that bundle existing forensic primitives into the views
operations leads actually use:

  GET /operations/review/overview            ← one-trip SLA review-meeting bundle
  GET /operations/engineer-load/overload-risk ← composite overload + SPOF score
  GET /operations/comparison/{queue_a}/{queue_b} ← side-by-side numerical delta

No new SQL semantics — we orchestrate SLALossEngine, InactivityEngine,
QueueForensicsService, OwnerForensicsService, queue_command_center.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from app.core.database import sync_session_factory
from app.core.dependencies import get_current_user
from app.services.forensics.inactivity_engine import InactivityEngine
from app.services.forensics.owner_forensics import OwnerForensicsService
from app.services.forensics.queue_forensics import QueueForensicsService
from app.services.forensics.sla_loss_engine import SLALossEngine

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


# ─────────────────────────────────────────────────────────────────────
# 1. SLA REVIEW OVERVIEW — single bundle for the weekly review meeting
# ─────────────────────────────────────────────────────────────────────

@router.get("/review/overview")
def review_overview(
    queue: list[str] = Query(default=[],
        description="Optional queue scope for review (favorites-aware)."),
):
    """Bundle everything an SLA review presenter needs:
    top loss queues, parking lots, dying tickets, silent breaches,
    bounce hotspots, no-owner queues, hidden-breach delta.
    """
    qs = queue or None
    with sync_session_factory() as db:
        # 1. Top SLA-loss queues — "where time was lost"
        top_loss = SLALossEngine.top_loss_queues(db, limit=10, queues=qs)
        # 2. No-owner parking lots
        parking = SLALossEngine.parking_lots(db, limit=10, queues=qs)
        # 3. Tickets dying in queue
        dying = SLALossEngine.dying_in_queue(db, limit=15, queues=qs)
        # 4. Silent breaches
        silent = InactivityEngine.detect_silent_breaches(
            db, min_inactivity_ratio=0.5, limit=15, queues=qs,
        )
        # 5. Worst routing chains — hot-potato + bounce hotspots
        hot_potato = QueueForensicsService.hot_potato_tickets(
            db, min_moves=3, limit=10, queues=qs,
        )
        # 6. Most overloaded engineers (top 10 by load_hours)
        engineers = OwnerForensicsService.compute_all(db, limit=10, queues=qs)
        # 7. Hidden-breach delta — wall_resolution_time breaches - resolution_time breaches
        delta_row = db.execute(
            text("""
                SELECT
                  COUNT(*) FILTER (WHERE metric_name='wall_resolution_time' AND sla_breached) AS wall_b,
                  COUNT(*) FILTER (WHERE metric_name='resolution_time' AND sla_breached) AS active_b
                FROM sla_metrics
                WHERE (:has_q IS FALSE OR queue_name = ANY(:qlist))
            """),
            {"has_q": bool(qs), "qlist": qs or []},
        ).mappings().first() or {}
        wall_b = int(delta_row.get("wall_b") or 0)
        active_b = int(delta_row.get("active_b") or 0)
        hidden = max(0, wall_b - active_b)

    return {
        "scope_queues": qs or [],
        "top_loss_queues": top_loss,
        "parking_lots": parking,
        "dying_in_queue": dying,
        "silent_breaches": [s.__dict__ if hasattr(s, "__dict__") else s for s in silent],
        "hot_potato": hot_potato,
        "overloaded_engineers": [
            e.__dict__ if hasattr(e, "__dict__") else e
            for e in engineers
        ],
        "hidden_breach_delta": {
            "wall_breaches": wall_b,
            "active_breaches": active_b,
            "hidden_breaches": hidden,
        },
    }


# ─────────────────────────────────────────────────────────────────────
# 2. ENGINEER LOAD INTELLIGENCE — overload + SPOF risk
# ─────────────────────────────────────────────────────────────────────

@router.get("/engineer-load/overload-risk")
def engineer_overload_risk(
    threshold_ratio: float = Query(2.0, ge=1.0, le=20.0,
        description="hours_owned/160 above this flags as overloaded."),
    queue: list[str] = Query(default=[]),
):
    """Surfaces operational risks at the human level:

      - overload_ratio       = hours_owned / 160 (monthly FTE)
      - spof_risk            = how many distinct queues this person
                               is the sole non-system owner of
      - bounce_burden        = sum of bounces on tickets they ever held
      - reassign_pressure    = times this owner was reassigned-FROM
      - load_balance_score   = 0..1; 1 = healthy, 0 = single carrier

    A SINGLE engineer carrying >=2 distinct queues alone is the
    AANOSOV pattern that the v1.9 dataset surfaced (19 Workplace-Veshki
    + 7 Asset-Veshki tickets = 1538h).
    """
    with sync_session_factory() as db:
        # Base load
        base_rows = db.execute(
            text("""
                SELECT op.owner,
                       COUNT(DISTINCT op.ticket_id) AS tickets,
                       SUM(EXTRACT(EPOCH FROM
                         (COALESCE(op.end_time, NOW()) - op.start_time)))::bigint
                         AS owned_seconds,
                       COUNT(DISTINCT op.queue_name) AS distinct_queues
                FROM ownership_periods op
                WHERE op.owner IS NOT NULL
                  AND LOWER(op.owner) NOT IN
                      ('root@localhost','otrs admin (root@localhost)','')
                  AND ((:has_q IS FALSE) OR op.queue_name = ANY(:qlist))
                GROUP BY op.owner
            """),
            {"has_q": bool(queue), "qlist": queue or []},
        ).mappings().all()

        # SPOF: queues where this owner is the ONLY non-system owner
        spof_rows = db.execute(
            text("""
                WITH per_q AS (
                  SELECT queue_name,
                         COUNT(DISTINCT owner) FILTER (
                           WHERE LOWER(owner) NOT IN
                                 ('root@localhost','otrs admin (root@localhost)','')
                             AND owner IS NOT NULL
                         ) AS unique_owners,
                         MAX(owner) FILTER (
                           WHERE LOWER(owner) NOT IN
                                 ('root@localhost','otrs admin (root@localhost)','')
                             AND owner IS NOT NULL
                         ) AS sole_owner
                  FROM ownership_periods
                  WHERE ((:has_q IS FALSE) OR queue_name = ANY(:qlist))
                  GROUP BY queue_name
                  HAVING COUNT(DISTINCT owner) FILTER (
                           WHERE LOWER(owner) NOT IN
                                 ('root@localhost','otrs admin (root@localhost)','')
                             AND owner IS NOT NULL
                         ) = 1
                )
                SELECT sole_owner, COUNT(*) AS spof_queues,
                       ARRAY_AGG(queue_name ORDER BY queue_name) AS queues
                FROM per_q
                GROUP BY sole_owner
            """),
            {"has_q": bool(queue), "qlist": queue or []},
        ).mappings().all()
        spof_map: dict[str, dict] = {
            r["sole_owner"]: {"count": int(r["spof_queues"]),
                              "queues": list(r["queues"] or [])}
            for r in spof_rows
        }

        # Reassign pressure — times someone took ownership AWAY
        reassign_rows = db.execute(
            text("""
                SELECT old_owner AS owner, COUNT(*) AS times_reassigned_from
                FROM ticket_events
                WHERE old_owner IS NOT NULL AND new_owner IS NOT NULL
                  AND old_owner != new_owner
                  AND ((:has_q IS FALSE) OR queue_name = ANY(:qlist))
                GROUP BY old_owner
            """),
            {"has_q": bool(queue), "qlist": queue or []},
        ).mappings().all()
        reassign_map = {r["owner"]: int(r["times_reassigned_from"]) for r in reassign_rows}

    rows = []
    for r in base_rows:
        hours = (int(r["owned_seconds"] or 0)) / 3600.0
        overload = round(hours / 160.0, 2)
        spof = spof_map.get(r["owner"], {"count": 0, "queues": []})
        # load_balance_score: penalise SPOF + overload; clamp 0..1
        penalty = 0.4 * min(1.0, overload / 5.0) + 0.4 * min(1.0, spof["count"] / 3.0)
        load_balance = round(max(0.0, 1.0 - penalty), 2)
        rows.append({
            "owner": r["owner"],
            "tickets": int(r["tickets"] or 0),
            "hours_owned": round(hours, 1),
            "overload_ratio": overload,
            "distinct_queues": int(r["distinct_queues"] or 0),
            "spof_risk_queues": spof["count"],
            "spof_queue_names": spof["queues"],
            "reassign_pressure": reassign_map.get(r["owner"], 0),
            "load_balance_score": load_balance,
            "flag_overloaded": overload >= threshold_ratio,
            "flag_spof": spof["count"] >= 1,
        })
    rows.sort(key=lambda x: (-x["overload_ratio"], -x["spof_risk_queues"]))
    flagged = [r for r in rows if r["flag_overloaded"] or r["flag_spof"]]
    return {
        "threshold_ratio": threshold_ratio,
        "scope_queues": queue or [],
        "engineer_count": len(rows),
        "flagged_count": len(flagged),
        "engineers": rows,
        "flagged_engineers": flagged,
    }


# ─────────────────────────────────────────────────────────────────────
# 3. PAIR COMPARISON — numerical delta between two queues
# ─────────────────────────────────────────────────────────────────────

@router.get("/comparison/{queue_a:path}/vs/{queue_b:path}")
def queue_comparison(queue_a: str, queue_b: str):
    """Side-by-side numerical delta. Designed for the
    Workplace-Veshki vs Plaza and AssetManagement-Veshki vs Plaza
    operational reviews.
    """
    def _profile(db, q: str) -> dict[str, Any]:
        exists = db.execute(
            text("SELECT 1 FROM ticket_snapshots WHERE current_queue = :q LIMIT 1"),
            {"q": q},
        ).scalar()
        if not exists:
            raise HTTPException(404, f"Queue '{q}' not found in snapshots")
        snap = db.execute(
            text("""
                SELECT COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE is_closed = FALSE) AS open_n
                FROM ticket_snapshots WHERE current_queue = :q
            """),
            {"q": q},
        ).mappings().first() or {}
        m = db.execute(
            text("""
                SELECT metric_name,
                       COUNT(*) AS n,
                       COUNT(*) FILTER (WHERE sla_breached) AS breaches,
                       AVG(metric_seconds)::bigint AS avg_sec
                FROM sla_metrics WHERE queue_name = :q
                  AND metric_name IN ('first_response_time','resolution_time',
                                      'wall_resolution_time')
                GROUP BY metric_name
            """),
            {"q": q},
        ).mappings().all()
        metrics: dict[str, dict] = {}
        for r in m:
            n = int(r["n"] or 0)
            br = int(r["breaches"] or 0)
            metrics[r["metric_name"]] = {
                "n": n,
                "breaches": br,
                "breach_pct": round(br / n * 100, 2) if n else 0.0,
                "avg_seconds": int(r["avg_sec"] or 0),
            }
        # No-owner share for this queue
        no_own = db.execute(
            text(f"""
                SELECT
                  SUM(EXTRACT(EPOCH FROM
                    (COALESCE(end_time, NOW()) - start_time)))::bigint AS total_sec,
                  SUM(CASE WHEN owner IS NULL OR LOWER(owner) IN
                       ('root@localhost','otrs admin (root@localhost)','')
                       THEN EXTRACT(EPOCH FROM
                            (COALESCE(end_time, NOW()) - start_time))
                       ELSE 0 END)::bigint AS no_own_sec
                FROM ownership_periods WHERE queue_name = :q
            """),
            {"q": q},
        ).mappings().first() or {}
        total_sec = int(no_own.get("total_sec") or 0)
        no_own_sec = int(no_own.get("no_own_sec") or 0)
        return {
            "queue": q,
            "total_tickets": int(snap.get("total") or 0),
            "open_now": int(snap.get("open_n") or 0),
            "metrics": metrics,
            "no_owner_pct": round(no_own_sec / total_sec * 100, 2) if total_sec else 0.0,
            "total_owned_hours": round(total_sec / 3600.0, 1),
            "no_owner_hours": round(no_own_sec / 3600.0, 1),
        }

    with sync_session_factory() as db:
        a = _profile(db, queue_a)
        b = _profile(db, queue_b)

    def _delta(field: str, k1: str | None = None) -> dict[str, Any]:
        v_a = a[field] if k1 is None else a["metrics"].get(field, {}).get(k1, 0)
        v_b = b[field] if k1 is None else b["metrics"].get(field, {}).get(k1, 0)
        return {"a": v_a, "b": v_b, "delta": v_a - v_b}

    return {
        "a": a,
        "b": b,
        "delta": {
            "total_tickets":        _delta("total_tickets"),
            "open_now":             _delta("open_now"),
            "no_owner_pct":         _delta("no_owner_pct"),
            "mtta_breach_pct":      _delta("first_response_time", "breach_pct"),
            "mttr_breach_pct":      _delta("resolution_time", "breach_pct"),
            "wall_resolution_breach_pct": _delta("wall_resolution_time", "breach_pct"),
        },
    }
