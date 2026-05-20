"""Advanced analytics engine — trend analysis, forecasting, correlation engine, SLA cost analytics."""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.database import sync_session_factory
from app.domain.models import SLAMetric, QueuePeriod, TicketEvent, TicketSnapshot, OwnershipPeriod

logger = logging.getLogger(__name__)


# === TREND ENGINE ===

def analyze_trends(days: int = 90) -> dict:
    """Analyze SLA trends — seasonality, degradation, recurring incidents, queue drift."""
    db = sync_session_factory()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        daily = db.execute(
            text("""
                SELECT date_trunc('day', computed_at) AS day,
                       COUNT(*) AS total,
                       SUM(CASE WHEN sla_breached THEN 1 ELSE 0 END) AS breaches
                FROM sla_metrics
                WHERE computed_at >= :since
                GROUP BY day ORDER BY day
            """),
            {"since": since},
        ).all()

        days_data = []
        for r in daily:
            rate = (r.breaches / max(r.total, 1)) * 100
            days_data.append({"date": str(r.day.date()), "breach_pct": round(rate, 2)})

        # Seasonality — breach rate by day of week
        dow = db.execute(
            text("""
                SELECT EXTRACT(DOW FROM computed_at) AS dow,
                       COUNT(*) AS total,
                       SUM(CASE WHEN sla_breached THEN 1 ELSE 0 END) AS breaches
                FROM sla_metrics
                WHERE computed_at >= :since
                GROUP BY dow ORDER BY dow
            """),
            {"since": since},
        ).all()

        dow_names = ["Вс", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]
        seasonality = []
        for r in dow:
            rate = (r.breaches / max(r.total, 1)) * 100
            seasonality.append({"day": dow_names[int(r.dow)], "breach_pct": round(rate, 2)})

        # Degradation trend (last 7 days vs previous 7)
        recent_7 = now = datetime.now(timezone.utc)
        r1 = db.execute(
            text("""
                SELECT COUNT(*) AS total, SUM(CASE WHEN sla_breached THEN 1 ELSE 0 END) AS breaches
                FROM sla_metrics WHERE computed_at >= :since AND computed_at < :now
            """),
            {"since": recent_7 - timedelta(days=7), "now": recent_7},
        ).first()
        r2 = db.execute(
            text("""
                SELECT COUNT(*) AS total, SUM(CASE WHEN sla_breached THEN 1 ELSE 0 END) AS breaches
                FROM sla_metrics WHERE computed_at >= :since AND computed_at < :now
            """),
            {"since": recent_7 - timedelta(days=14), "now": recent_7 - timedelta(days=7)},
        ).first()

        recent_rate = (r1.breaches / max(r1.total, 1)) * 100 if r1 else 0
        prev_rate = (r2.breaches / max(r2.total, 1)) * 100 if r2 else 0
        degradation = round(recent_rate - prev_rate, 2)

        return {
            "daily_breach_rates": days_data,
            "seasonality": seasonality,
            "degradation_7d": {
                "recent_breach_pct": round(recent_rate, 2),
                "previous_breach_pct": round(prev_rate, 2),
                "delta": degradation,
                "trend": "degrading" if degradation > 5 else "improving" if degradation < -5 else "stable",
            },
            "worst_day": max(seasonality, key=lambda x: x["breach_pct"]) if seasonality else None,
            "best_day": min(seasonality, key=lambda x: x["breach_pct"]) if seasonality else None,
        }
    finally:
        db.close()


# === FORECASTING ===

def forecast_breaches(days_ahead: int = 14) -> dict:
    """Predict future breach rates using linear regression on daily data."""
    db = sync_session_factory()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=90)
        daily = db.execute(
            text("""
                SELECT date_trunc('day', computed_at) AS day,
                       COUNT(*) AS total,
                       SUM(CASE WHEN sla_breached THEN 1 ELSE 0 END) AS breaches
                FROM sla_metrics
                WHERE computed_at >= :since
                GROUP BY day ORDER BY day
            """),
            {"since": since},
        ).all()

        if len(daily) < 7:
            return {"error": "Недостаточно данных для прогноза (нужно минимум 7 дней)"}

        x_vals = list(range(len(daily)))
        y_vals = [(r.breaches / max(r.total, 1)) * 100 for r in daily]

        n = len(x_vals)
        sx = sum(x_vals)
        sy = sum(y_vals)
        sxx = sum(x * x for x in x_vals)
        sxy = sum(x * y for x, y in zip(x_vals, y_vals))

        slope = (n * sxy - sx * sy) / max(n * sxx - sx * sx, 1)
        intercept = (sy - slope * sx) / max(n, 1)

        forecast = []
        last_day = daily[-1].day
        for i in range(1, days_ahead + 1):
            pred_x = n + i
            pred_val = max(0, slope * pred_x + intercept)
            pred_date = last_day + timedelta(days=i)
            forecast.append({"date": str(pred_date.date()), "predicted_breach_pct": round(pred_val, 2)})

        # Overload windows
        overload_windows = [f for f in forecast if f["predicted_breach_pct"] > 20]

        return {
            "forecast": forecast,
            "slope": round(slope, 4),
            "trend_direction": "improving" if slope < 0 else "worsening",
            "predicted_overload_days": len(overload_windows),
            "overload_windows": overload_windows,
            "confidence": "high" if len(daily) > 30 else "medium" if len(daily) > 14 else "low",
        }
    finally:
        db.close()


def queue_saturation_forecast(days_ahead: int = 7) -> list[dict]:
    """Predict queue saturation — which queues will be overloaded."""
    db = sync_session_factory()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=30)
        queue_stats = db.query(
            QueuePeriod.queue_name,
            func.count(func.distinct(QueuePeriod.ticket_id)).label("ticket_count"),
            func.avg(QueuePeriod.duration_seconds).label("avg_duration"),
        ).filter(
            QueuePeriod.entered_at >= since,
            QueuePeriod.queue_name.isnot(None),
        ).group_by(QueuePeriod.queue_name).all()

        results = []
        for q in queue_stats:
            tickets_per_day = q.ticket_count / 30.0
            avg_hours = (q.avg_duration or 0) / 3600
            saturation_score = round(tickets_per_day * avg_hours, 2)
            if saturation_score > 0:
                results.append({
                    "queue": q.queue_name,
                    "current_tickets_per_day": round(tickets_per_day, 2),
                    "avg_resolution_hours": round(avg_hours, 2),
                    "saturation_score": saturation_score,
                    "risk_level": "high" if saturation_score > 50 else "medium" if saturation_score > 20 else "low",
                    "predicted_overload_in_days": max(1, int(30 / max(tickets_per_day, 0.1))),
                })

        return sorted(results, key=lambda x: x["saturation_score"], reverse=True)
    finally:
        db.close()


# === CORRELATION ENGINE ===

def find_correlations() -> dict:
    """Find correlations between queues, agents, imports, and SLA failures."""
    db = sync_session_factory()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=90)

        # Queue-queue correlation (which queues share tickets)
        queue_corr = db.execute(
            text("""
                SELECT a.queue_name AS queue_a, b.queue_name AS queue_b, COUNT(*) AS shared_tickets
                FROM (
                    SELECT ticket_id, queue_name FROM queue_periods WHERE entered_at >= :since AND queue_name IS NOT NULL
                ) a
                JOIN (
                    SELECT ticket_id, queue_name FROM queue_periods WHERE entered_at >= :since AND queue_name IS NOT NULL
                ) b ON a.ticket_id = b.ticket_id AND a.queue_name < b.queue_name
                GROUP BY queue_a, queue_b
                ORDER BY shared_tickets DESC
                LIMIT 20
            """),
            {"since": since},
        ).all()

        # Agent-queue correlation
        agent_queue = db.execute(
            text("""
                SELECT op.owner, op.queue_name, COUNT(*) AS interactions
                FROM ownership_periods op
                WHERE op.start_time >= :since AND op.owner IS NOT NULL AND op.queue_name IS NOT NULL
                GROUP BY op.owner, op.queue_name
                ORDER BY interactions DESC
                LIMIT 30
            """),
            {"since": since},
        ).all()

        return {
            "queue_correlations": [{"queue_a": r.queue_a, "queue_b": r.queue_b, "shared_tickets": r.shared_tickets} for r in queue_corr],
            "agent_queue_affinity": [{"owner": r.owner, "queue": r.queue_name, "interactions": r.interactions} for r in agent_queue],
        }
    finally:
        db.close()


# === SLA COST ANALYTICS ===

def estimate_sla_costs() -> dict:
    """Estimate operational cost of SLA breaches and queue inefficiency."""
    db = sync_session_factory()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=30)
        now = datetime.now(timezone.utc)

        # Breach cost estimate (assume $50 per breach incident)
        BREACH_COST = 50
        total_breaches = db.query(func.count(SLAMetric.id)).filter(
            SLAMetric.sla_breached == True,
            SLAMetric.computed_at >= since,
        ).scalar() or 0

        breach_cost = total_breaches * BREACH_COST

        # Queue inefficiency cost (time wasted in stalled queues, $1/min)
        INEFFICIENCY_COST_PER_MIN = 1
        stalled_seconds = db.query(func.sum(QueuePeriod.duration_seconds)).filter(
            QueuePeriod.exited_at.is_(None),
            QueuePeriod.entered_at >= since,
            QueuePeriod.duration_seconds > 3600,  # > 1h
        ).scalar() or 0

        inefficiency_cost = (stalled_seconds / 60) * INEFFICIENCY_COST_PER_MIN

        # Cost by queue
        queue_costs = db.execute(
            text("""
                SELECT m.queue_name,
                       COUNT(*) AS total_metrics,
                       SUM(CASE WHEN m.sla_breached THEN 1 ELSE 0 END) AS breaches,
                       AVG(m.metric_seconds) AS avg_seconds
                FROM sla_metrics m
                WHERE m.computed_at >= :since AND m.queue_name IS NOT NULL
                GROUP BY m.queue_name
                ORDER BY breaches DESC
            """),
            {"since": since},
        ).all()

        cost_by_queue = []
        for r in queue_costs:
            b = r.breaches or 0
            queue_cst = b * BREACH_COST
            cost_by_queue.append({
                "queue": r.queue_name,
                "breaches": b,
                "estimated_cost": queue_cst,
            })

        return {
            "period_days": 30,
            "total_breaches": total_breaches,
            "breach_cost_usd": breach_cost,
            "inefficiency_cost_usd": round(inefficiency_cost, 2),
            "total_estimated_cost_usd": round(breach_cost + inefficiency_cost, 2),
            "cost_by_queue": cost_by_queue,
            "assumptions": {
                "breach_cost_per_incident": BREACH_COST,
                "stalled_time_cost_per_min": INEFFICIENCY_COST_PER_MIN,
            },
        }
    finally:
        db.close()
