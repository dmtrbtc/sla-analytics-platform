"""Materialized view refresh management."""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

MATERIALIZED_VIEWS = [
    "mv_sla_summary_daily",
    "mv_queue_performance_daily",
    "mv_team_metrics_daily",
]


def refresh_all_views(db: Session, concurrently: bool = True) -> dict[str, str]:
    """Refresh all materialized views, optionally CONCURRENTLY."""
    results = {}
    for view in MATERIALIZED_VIEWS:
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
    if view_name not in MATERIALIZED_VIEWS:
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
