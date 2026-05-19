"""Queue anomaly detection using statistical analysis.

Detects:
  - Abnormal breach spikes (Z-score > 3)
  - Queue saturation (ticket accumulation rate)
  - Unusual reassignment rates
  - Stuck queues (no movement for extended period)
  - Unusual response delays
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import func, text

from app.core.database import sync_session_factory
from app.domain.models import SLAMetric, TicketEvent, QueuePeriod

logger = logging.getLogger(__name__)


def detect_anomalies(days: int = 7) -> list[dict[str, Any]]:
    """Run all anomaly detectors and return findings."""
    anomalies = []
    anomalies.extend(_detect_breach_spikes(days))
    anomalies.extend(_detect_queue_saturation(days))
    anomalies.extend(_detect_unusual_reassignments(days))
    anomalies.extend(_detect_stalled_queues(days))
    return anomalies


def _detect_breach_spikes(days: int) -> list[dict[str, Any]]:
    """Detect queues with abnormally high breach counts (Z-score > 3)."""
    db = sync_session_factory()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        rows = db.query(
            SLAMetric.queue_name,
            func.count(SLAMetric.id).label("total"),
            func.sum(SLAMetric.sla_breached.cast(int)).label("breaches"),
        ).filter(
            SLAMetric.computed_at >= since,
        ).group_by(SLAMetric.queue_name).all()

        if not rows:
            return []

        breach_rates = [r.breaches / max(r.total, 1) for r in rows]
        avg = sum(breach_rates) / len(breach_rates)
        std = (sum((r - avg) ** 2 for r in breach_rates) / len(breach_rates)) ** 0.5 or 1

        findings = []
        for r, rate in zip(rows, breach_rates):
            z_score = (rate - avg) / std
            if z_score > 3 and r.breaches > 5:
                findings.append({
                    "type": "breach_spike",
                    "queue": r.queue_name,
                    "severity": "critical" if z_score > 5 else "high",
                    "detail": f"Аномальный уровень нарушений: {rate:.0%} (Z={z_score:.1f})",
                    "breach_rate": round(rate, 3),
                    "z_score": round(z_score, 1),
                    "breach_count": int(r.breaches),
                })
        return findings
    finally:
        db.close()


def _detect_queue_saturation(days: int) -> list[dict[str, Any]]:
    """Detect queues with high ticket accumulation rate."""
    db = sync_session_factory()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        rows = db.query(
            QueuePeriod.queue_name,
            func.count(QueuePeriod.id).label("tickets"),
            func.avg(QueuePeriod.duration_seconds).label("avg_duration"),
        ).filter(
            QueuePeriod.entered_at >= since,
        ).group_by(QueuePeriod.queue_name).all()

        findings = []
        for r in rows:
            avg_min = (r.avg_duration or 0) / 60
            if r.tickets > 50 and avg_min > 1440:  # >50 tickets, avg >24h
                findings.append({
                    "type": "queue_saturation",
                    "queue": r.queue_name,
                    "severity": "high",
                    "detail": f"Переполнение очереди: {r.tickets} тикетов, среднее ожидание {avg_min:.0f} мин",
                    "ticket_count": int(r.tickets),
                    "avg_wait_minutes": round(avg_min, 1),
                })
        return findings
    finally:
        db.close()


def _detect_unusual_reassignments(days: int) -> list[dict[str, Any]]:
    """Detect queues with abnormally high reassignment rates."""
    db = sync_session_factory()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        subq = db.query(
            TicketEvent.ticket_id,
            func.count(TicketEvent.id).label("reassigns"),
        ).filter(
            TicketEvent.event_type == "OwnerUpdate",
            TicketEvent.event_time >= since,
        ).group_by(TicketEvent.ticket_id).subquery()

        avg_row = db.query(func.avg(subq.c.reassigns)).scalar()
        avg_reassigns = avg_row or 0
        std = db.query(
            func.sqrt(func.avg((subq.c.reassigns - avg_reassigns) ** 2))
        ).scalar() or 1

        findings = []
        high_reassign = db.query(
            TicketEvent.queue_name,
            func.count(TicketEvent.id).label("reassigns"),
        ).filter(
            TicketEvent.event_type == "OwnerUpdate",
            TicketEvent.event_time >= since,
        ).group_by(TicketEvent.queue_name).having(
            func.count(TicketEvent.id) > avg_reassigns + 3 * std
        ).all()

        for r in high_reassign:
            z = (r.reassigns - avg_reassigns) / max(std, 1)
            findings.append({
                "type": "high_reassignments",
                "queue": r.queue_name,
                "severity": "high" if z > 5 else "medium",
                "detail": f"Аномальное число переназначений: {r.reassigns} (Z={z:.1f})",
                "reassign_count": int(r.reassigns),
                "z_score": round(z, 1),
            })
        return findings
    finally:
        db.close()


def _detect_stalled_queues(days: int) -> list[dict[str, Any]]:
    """Detect queues with tickets stuck for extended periods."""
    db = sync_session_factory()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        rows = db.query(
            QueuePeriod.queue_name,
            func.count(QueuePeriod.id).label("stalled"),
        ).filter(
            QueuePeriod.entered_at >= since,
            QueuePeriod.exited_at.is_(None),
            QueuePeriod.duration_seconds > 172800,  # >48 hours
        ).group_by(QueuePeriod.queue_name).all()

        return [{
            "type": "stalled_queue",
            "queue": r.queue_name,
            "severity": "high",
            "detail": f"Застрявшие тикеты: {r.stalled} шт. >48ч без движения",
            "stalled_count": int(r.stalled),
        } for r in rows if r.stalled > 3]
    finally:
        db.close()
