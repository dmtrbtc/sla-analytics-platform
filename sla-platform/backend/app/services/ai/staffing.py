"""Staffing recommendation engine.

Computes:
  - Overloaded teams based on ticket volume vs agent count
  - Recommended staffing levels
  - Predicted backlog growth
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import func, text

from app.core.database import sync_session_factory
from app.domain.models import TicketSnapshot, OwnershipPeriod, Team

logger = logging.getLogger(__name__)


def get_staffing_recommendations(days: int = 30) -> list[dict[str, Any]]:
    """Analyze team workload and generate staffing recommendations."""
    db = sync_session_factory()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Get all teams with their prefix
        teams = db.query(Team).all()
        if not teams:
            return []

        recommendations = []
        for team in teams:
            prefix = team.prefix
            # Tickets assigned to this team's prefix
            ticket_count = db.query(func.count(TicketSnapshot.id)).filter(
                TicketSnapshot.current_queue.like(f"{prefix}%"),
                TicketSnapshot.is_closed == False,
            ).scalar() or 0

            # Unique owners in this team
            owner_count = db.query(func.count(func.distinct(OwnershipPeriod.owner))).filter(
                OwnershipPeriod.team_prefix == prefix,
                OwnershipPeriod.start_time >= since,
            ).scalar() or 1

            tickets_per_owner = ticket_count / owner_count
            overloaded = tickets_per_owner > 20

            # Predicted growth (linear regression over 7 days)
            predicted_growth = _predict_growth(db, prefix)

            recommendations.append({
                "team_name": team.name,
                "team_prefix": prefix,
                "open_tickets": ticket_count,
                "unique_owners": owner_count,
                "tickets_per_owner": round(tickets_per_owner, 1),
                "overloaded": overloaded,
                "recommended_staffing": max(1, round(ticket_count / 15)),
                "current_staffing": owner_count,
                "predicted_backlog_growth": round(predicted_growth, 0),
                "severity": "critical" if tickets_per_owner > 40 else ("high" if overloaded else "info"),
            })

        return sorted(recommendations, key=lambda r: r["tickets_per_owner"], reverse=True)
    finally:
        db.close()


def _predict_growth(db, prefix: str) -> float:
    """Simple linear regression to predict ticket growth."""
    from sqlalchemy import text as sql_text
    try:
        row = db.execute(sql_text("""
            WITH daily AS (
                SELECT
                    date_trunc('day', entered_at) AS day,
                    COUNT(*) AS tickets
                FROM ownership_periods
                WHERE team_prefix = :prefix
                  AND entered_at >= NOW() - INTERVAL '7 days'
                GROUP BY date_trunc('day', entered_at)
                ORDER BY day
            )
            SELECT
                COUNT(*) AS n,
                SUM(EXTRACT(EPOCH FROM day)) AS sum_x,
                SUM(tickets) AS sum_y,
                SUM(EXTRACT(EPOCH FROM day) * tickets) AS sum_xy,
                SUM(EXTRACT(EPOCH FROM day) ^ 2) AS sum_xx
            FROM daily
        """), {"prefix": prefix}).first()

        if not row or row.n < 2:
            return 0.0

        n = row.n
        sum_x = row.sum_x
        sum_y = row.sum_y
        sum_xy = row.sum_xy
        sum_xx = row.sum_xx

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x) if (n * sum_xx - sum_x * sum_x) != 0 else 0
        return slope * 86400 * 7  # predicted weekly growth
    except Exception:
        return 0.0
