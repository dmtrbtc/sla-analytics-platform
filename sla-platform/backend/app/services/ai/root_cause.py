"""Root cause hint generator for operational anomalies.

Generates human-readable operational hints in Russian:
  - "Очередь Support перегружена из-за роста тикетов Billing"
  - "Высокий процент переназначений у команды L2"
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import func

from app.core.database import sync_session_factory
from app.domain.models import SLAMetric, TicketEvent, QueuePeriod, TicketSnapshot

logger = logging.getLogger(__name__)


def generate_hints(days: int = 7) -> list[dict[str, Any]]:
    """Generate operational intelligence hints."""
    db = sync_session_factory()
    try:
        hints = []
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # 1. Queue overload hints
        overloaded = db.query(
            QueuePeriod.queue_name,
            func.count(QueuePeriod.id).label("tickets"),
        ).filter(
            QueuePeriod.entered_at >= since,
            QueuePeriod.exited_at.is_(None),
        ).group_by(QueuePeriod.queue_name).order_by(func.count(QueuePeriod.id).desc()).limit(5).all()

        for q in overloaded:
            hints.append({
                "type": "queue_overload",
                "severity": "high" if q.tickets > 20 else "info",
                "message": f"Очередь {q.queue_name} перегружена: {q.tickets} активных тикетов",
            })

        # 2. High reassignment hints
        high_reassign = db.query(
            TicketEvent.queue_name,
            func.count(TicketEvent.id).label("reassigns"),
        ).filter(
            TicketEvent.event_type == "OwnerUpdate",
            TicketEvent.event_time >= since,
        ).group_by(TicketEvent.queue_name).order_by(func.count(TicketEvent.id).desc()).limit(5).all()

        for q in high_reassign:
            if q.reassigns > 10:
                hints.append({
                    "type": "high_reassignments",
                    "severity": "medium",
                    "message": f"Высокий процент переназначений в очереди {q.queue_name}: {q.reassigns}",
                })

        # 3. SLA breach hotspots
        hotspots = db.query(
            SLAMetric.queue_name,
            func.count(SLAMetric.id).label("breaches"),
        ).filter(
            SLAMetric.computed_at >= since,
            SLAMetric.sla_breached == True,
        ).group_by(SLAMetric.queue_name).order_by(func.count(SLAMetric.id).desc()).limit(5).all()

        for q in hotspots:
            hints.append({
                "type": "breach_hotspot",
                "severity": "high" if q.breaches > 10 else "warning",
                "message": f"Рост нарушений SLA в очереди {q.queue_name}: {q.breaches} нарушений",
            })

        # 4. Stagnant tickets
        stagnant = db.query(
            QueuePeriod.queue_name,
            func.count(QueuePeriod.id).label("stalled"),
        ).filter(
            QueuePeriod.entered_at >= since,
            QueuePeriod.exited_at.is_(None),
            QueuePeriod.duration_seconds > 86400 * 3,  # 3 days
        ).group_by(QueuePeriod.queue_name).order_by(func.count(QueuePeriod.id).desc()).limit(5).all()

        for q in stagnant:
            if q.stalled > 3:
                hints.append({
                    "type": "stagnant_tickets",
                    "severity": "warning",
                    "message": f"Зависшие тикеты в очереди {q.queue_name}: {q.stalled} шт. >3 дней",
                })

        return hints
    finally:
        db.close()
