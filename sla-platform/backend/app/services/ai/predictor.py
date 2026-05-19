"""Breach prediction engine using statistical heuristics.

Predicts SLA breach probability per ticket based on:
- Elapsed time vs target
- Queue historical breach rate
- Reassignment count
- Current risk level
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.domain.models import SLAMetric, TicketSnapshot
from app.core.database import sync_session_factory

logger = logging.getLogger(__name__)


def predict_breach_probability(
    ticket_id: int,
    elapsed_seconds: Optional[float] = None,
    response_target: Optional[int] = None,
    resolution_target: Optional[int] = None,
) -> dict[str, Any]:
    """Predict breach probability for a ticket using statistical heuristics.

    Returns dict with:
      - probability: 0.0-1.0
      - risk_reason: str
      - contributing_factors: list[str]
      - estimated_breach_eta: Optional[float] (seconds from now)
    """
    db = sync_session_factory()
    try:
        ticket = db.query(TicketSnapshot).filter(TicketSnapshot.ticket_id == ticket_id).first()
        if not ticket:
            return {"probability": 0.0, "risk_reason": "Тикет не найден", "contributing_factors": [], "estimated_breach_eta": None}

        # Get SLA metrics
        metrics = db.query(SLAMetric).filter(
            SLAMetric.ticket_id == ticket_id,
            SLAMetric.sla_breached == False,
        ).all()

        if not metrics:
            return {"probability": 0.0, "risk_reason": "Нет активных метрик SLA", "contributing_factors": [], "estimated_breach_eta": None}

        factors = []
        max_prob = 0.0
        min_eta = None

        for m in metrics:
            target = response_target or 3600
            if m.metric_name == "resolution_time":
                target = resolution_target or 86400
            elapsed = elapsed_seconds or (m.metric_seconds or 0)
            ratio = elapsed / target if target > 0 else 0

            # Queue historical breach rate as factor
            queue_breach_rate = _get_queue_breach_rate(db, ticket.current_queue or m.queue_name or "")
            if queue_breach_rate > 0.3:
                factors.append(f"Исторический уровень нарушений очереди: {queue_breach_rate:.0%}")

            # Reassignment factor
            if ticket.ticket_id:
                reassign_count = _get_reassign_count(db, ticket.ticket_id)
                if reassign_count > 5:
                    factors.append(f"Частые переназначения ({reassign_count})")
                if reassign_count > 10:
                    ratio *= 1.2

            # Risk level factor
            if m.risk_level in ("critical", "high"):
                factors.append(f"Текущий уровень риска: {m.risk_level}")
                ratio *= 1.3

            prob = min(ratio, 1.0)
            if prob > max_prob:
                max_prob = prob

            # ETA calculation
            remaining = target - elapsed
            if remaining > 0 and ratio > 0.5:
                eta = remaining * (1 - ratio)
                if min_eta is None or eta < min_eta:
                    min_eta = eta

        result = {
            "probability": round(max_prob, 2),
            "risk_reason": _get_risk_reason(max_prob),
            "contributing_factors": factors[:5],
            "estimated_breach_eta": round(min_eta) if min_eta else None,
        }
        return result
    finally:
        db.close()


def predict_batch(ticket_ids: list[int]) -> list[dict[str, Any]]:
    """Predict breach probability for multiple tickets."""
    return [predict_breach_probability(tid) for tid in ticket_ids]


def _get_queue_breach_rate(db, queue_name: str) -> float:
    from sqlalchemy import func
    total = db.query(func.count(SLAMetric.id)).filter(
        SLAMetric.queue_name == queue_name,
    ).scalar() or 1
    breached = db.query(func.count(SLAMetric.id)).filter(
        SLAMetric.queue_name == queue_name,
        SLAMetric.sla_breached == True,
    ).scalar() or 0
    return breached / total


def _get_reassign_count(db, ticket_id: int) -> int:
    from app.domain.models import TicketEvent
    return db.query(TicketEvent).filter(
        TicketEvent.ticket_id == ticket_id,
        TicketEvent.event_type == "OwnerUpdate",
    ).count()


def _get_risk_reason(prob: float) -> str:
    if prob >= 0.9:
        return "Критический риск нарушения SLA"
    if prob >= 0.7:
        return "Высокий риск нарушения SLA"
    if prob >= 0.4:
        return "Средний риск нарушения SLA"
    if prob >= 0.2:
        return "Низкий риск нарушения SLA"
    return "Риск нарушения SLA минимален"
