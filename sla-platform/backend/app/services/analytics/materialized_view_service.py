"""Materialized view refresh management with stale view detection and auto-refresh."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

MATERIALIZED_VIEWS = [
    "mv_sla_summary_daily",
    "mv_queue_performance_daily",
    "mv_team_metrics_daily",
]

# Additional extended views for deep analytics
EXTENDED_VIEWS = [
    "mv_breach_trends_daily",
    "mv_owner_performance_daily",
    "mv_queue_sla_compliance_daily",
]

ALL_VIEWS = MATERIALIZED_VIEWS + EXTENDED_VIEWS

EXTENDED_VIEW_SQL: dict[str, str] = {
    "mv_breach_trends_daily": """
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_breach_trends_daily AS
        SELECT
            date_trunc('day', computed_at) AS day,
            queue_name,
            metric_name,
            COUNT(*) AS total_metrics,
            COUNT(*) FILTER (WHERE sla_breached) AS breached_count,
            ROUND(
                COUNT(*) FILTER (WHERE sla_breached) * 100.0 / NULLIF(COUNT(*), 0), 2
            ) AS breach_pct,
            AVG(sla_risk_score)::numeric(10,2) AS avg_risk_score
        FROM sla_metrics
        WHERE queue_name IS NOT NULL
        GROUP BY date_trunc('day', computed_at), queue_name, metric_name
        WITH DATA
    """,
    "mv_owner_performance_daily": """
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_owner_performance_daily AS
        SELECT
            date_trunc('day', op.start_time) AS day,
            op.owner,
            op.team_prefix,
            COUNT(DISTINCT op.ticket_id) AS tickets_handled,
            AVG(op.duration_seconds)::numeric(10,2) AS avg_ownership_seconds,
            SUM(op.duration_seconds)::numeric(10,2) AS total_ownership_seconds,
            COUNT(*) FILTER (WHERE m.sla_breached) AS breaches_as_owner
        FROM ownership_periods op
        LEFT JOIN sla_metrics m ON m.ticket_id = op.ticket_id
            AND m.owner = op.owner
            AND date_trunc('day', m.computed_at) = date_trunc('day', op.start_time)
        GROUP BY date_trunc('day', op.start_time), op.owner, op.team_prefix
        WITH DATA
    """,
    "mv_queue_sla_compliance_daily": """
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_queue_sla_compliance_daily AS
        SELECT
            date_trunc('day', m.computed_at) AS day,
            m.queue_name,
            m.team_prefix,
            m.metric_name,
            d.name AS sla_definition_name,
            d.response_target_seconds,
            d.resolution_target_seconds,
            COUNT(*) AS total_metrics,
            COUNT(*) FILTER (WHERE m.sla_breached) AS breached_count,
            ROUND(
                COUNT(*) FILTER (WHERE m.sla_breached) * 100.0 / NULLIF(COUNT(*), 0), 2
            ) AS breach_pct,
            AVG(m.metric_seconds)::numeric(10,2) AS avg_seconds,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY m.metric_seconds)::numeric(10,2) AS median_seconds
        FROM sla_metrics m
        JOIN sla_definitions d ON d.id = m.sla_definition_id
        WHERE m.queue_name IS NOT NULL
        GROUP BY date_trunc('day', m.computed_at), m.queue_name, m.team_prefix,
                 m.metric_name, d.name, d.response_target_seconds, d.resolution_target_seconds
        WITH DATA
    """,
}


def check_view_staleness(db: Session) -> list[dict]:
    """Check if materialized views are stale (> 24h since last refresh)."""
    results = []
    for view in ALL_VIEWS:
        row = db.execute(
            text("""
                SELECT
                    relname,
                    pg_stat_get_last_vacuum_time(oid) AS last_refresh
                FROM pg_class
                WHERE relname = :name
            """),
            {"name": view},
        ).first()
        if row:
            last_refresh = row[1]
            is_stale = False
            if last_refresh:
                age = datetime.now(timezone.utc) - last_refresh.replace(tzinfo=timezone.utc)
                is_stale = age.total_seconds() > 86400
            results.append({
                "view_name": view,
                "exists": True,
                "last_refresh": str(last_refresh) if last_refresh else None,
                "is_stale": is_stale,
            })
        else:
            results.append({
                "view_name": view,
                "exists": False,
                "last_refresh": None,
                "is_stale": True,
            })
    return results


def ensure_extended_views(db: Session) -> list[str]:
    """Create extended materialized views if they don't exist."""
    created = []
    for name, sql in EXTENDED_VIEW_SQL.items():
        try:
            db.execute(text(sql))
            db.commit()
            created.append(name)
            logger.info("Created extended materialized view: %s", name)
        except Exception as exc:
            db.rollback()
            logger.warning("Could not create view %s: %s", name, exc)
    return created


def refresh_all_views(db: Session, concurrently: bool = True) -> dict[str, str]:
    """Refresh all materialized views, optionally CONCURRENTLY."""
    results = {}
    for view in ALL_VIEWS:
        try:
            sql = "REFRESH MATERIALIZED VIEW {conc} {name}".format(
                conc="CONCURRENTLY" if concurrently else "",
                name=view,
            )
            db.execute(text(sql))
            db.commit()
            results[view] = "refreshed"
            logger.info("Refreshed materialized view: %s", view)
        except Exception as exc:
            db.rollback()
            results[view] = f"error: {exc}"
            logger.error("Failed to refresh %s: %s", view, exc)
    return results


def refresh_view(db: Session, view_name: str, concurrently: bool = True) -> str:
    """Refresh a single materialized view."""
    if view_name not in ALL_VIEWS:
        return f"unknown view: {view_name}"
    try:
        sql = "REFRESH MATERIALIZED VIEW {conc} {name}".format(
            conc="CONCURRENTLY" if concurrently else "",
            name=view_name,
        )
        db.execute(text(sql))
        db.commit()
        return "refreshed"
    except Exception as exc:
        db.rollback()
        return f"error: {exc}"
