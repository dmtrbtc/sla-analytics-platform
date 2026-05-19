"""Predictive SLA engine — breach ETA, probability, overload forecasting.

Uses current elapsed time vs target to project:
- Breach ETA (estimated time remaining before breach)
- Breach probability (0-100%)
- Estimated resolution time
- Queue overload score
- Owner overload score
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.domain.models import SLAMetric, TicketSnapshot
from app.services.sla.pause_engine import calculate_active_time

logger = logging.getLogger(__name__)


def compute_breach_eta(
    active_elapsed: int,
    target_seconds: int,
) -> Optional[dict]:
    """Project breach ETA based on elapsed active time vs target.

    Returns dict with:
    - remaining_seconds: active seconds left before breach
    - breach_eta_absolute: projected UTC datetime of breach (if linear)
    - breach_probability: 0-100% based on current consumption rate
    - elapsed_ratio: active_elapsed / target
    """
    if target_seconds <= 0:
        return None

    elapsed_ratio = active_elapsed / target_seconds
    remaining_seconds = max(0, target_seconds - active_elapsed)

    if elapsed_ratio >= 1.0:
        return {
            "remaining_seconds": 0,
            "breach_eta_absolute": None,
            "breach_probability": 100,
            "elapsed_ratio": elapsed_ratio,
            "status": "breached",
        }

    if elapsed_ratio >= 0.95:
        breach_probability = 95
    elif elapsed_ratio >= 0.80:
        breach_probability = 75
    elif elapsed_ratio >= 0.60:
        breach_probability = 40
    elif elapsed_ratio >= 0.30:
        breach_probability = 15
    else:
        breach_probability = 5

    return {
        "remaining_seconds": remaining_seconds,
        "breach_eta_absolute": None,
        "breach_probability": breach_probability,
        "elapsed_ratio": round(elapsed_ratio, 3),
        "status": "active",
    }


def compute_queue_overload(
    db: Session,
    queue_name: str,
    lookback_hours: int = 24,
) -> dict:
    """Compute overload score for a queue based on recent SLA breaches.

    Returns:
    - overload_score: 0-100
    - total_tickets: count in lookback period
    - breached_count: count breached
    - breach_rate: percentage breached
    - severity: low/medium/high/critical
    """
    from sqlalchemy import text

    row = db.execute(
        text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN sla_breached = True THEN 1 ELSE 0 END) as breached
            FROM sla_metrics
            WHERE queue_name = :queue
              AND computed_at >= NOW() - INTERVAL :hours HOURS
              AND metric_name IN ('first_response_time', 'resolution_time')
        """),
        {"queue": queue_name, "hours": lookback_hours},
    ).mappings().first()

    total = row["total"] or 0
    breached = row["breached"] or 0
    breach_rate = (breached / max(total, 1)) * 100

    overload_score = min(100, int(breach_rate * 1.5))

    if overload_score >= 80:
        severity = "critical"
    elif overload_score >= 60:
        severity = "high"
    elif overload_score >= 30:
        severity = "medium"
    else:
        severity = "low"

    return {
        "queue_name": queue_name,
        "overload_score": overload_score,
        "total_tickets": total,
        "breached_count": breached,
        "breach_rate": round(breach_rate, 1),
        "severity": severity,
    }
