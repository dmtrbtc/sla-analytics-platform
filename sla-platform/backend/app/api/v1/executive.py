"""Executive Intelligence Suite — health score, financial impact, forecasts, MTTR, efficiency."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from app.core.database import sync_session_factory
from app.core.dependencies import get_current_user, require_admin
from app.domain.models import User

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/health-score")
async def sla_health_score(days: int = Query(30, ge=1, le=365), _: User = Depends(get_current_user)):
    """Overall SLA health score (0-100)."""
    db = sync_session_factory()
    try:
        row = db.execute(text("""
            SELECT COUNT(*) as total, SUM(CASE WHEN sla_breached THEN 1 ELSE 0 END) as breached
            FROM sla_metrics WHERE created_at >= NOW() - INTERVAL ':days days'
        """.replace(":days", str(days)))).first()
        total = row.total or 0
        breached = row.breached or 0
        compliance = ((total - breached) / max(total, 1)) * 100
        score = max(0, min(100, compliance))
        return {
            "score": round(score, 1),
            "compliance_pct": round(compliance, 1),
            "total_metrics": total,
            "total_breaches": breached,
            "status": "healthy" if score >= 95 else "warning" if score >= 85 else "critical",
        }
    finally:
        db.close()


@router.get("/financial-impact")
async def financial_impact(days: int = Query(90, ge=1, le=365), _: User = Depends(require_admin)):
    """Financial impact estimate of SLA breaches."""
    db = sync_session_factory()
    try:
        cost_per_breach = 50
        row = db.execute(text("""
            SELECT COUNT(*) as breaches,
                   COUNT(DISTINCT ticket_id) as affected_tickets,
                   MAX(metric_value_seconds) as worst_breach_seconds
            FROM sla_metrics WHERE sla_breached = true AND created_at >= NOW() - INTERVAL ':days days'
        """.replace(":days", str(days)))).first()
        breaches = row.breaches or 0
        total_cost = breaches * cost_per_breach
        return {
            "period_days": days,
            "total_breaches": breaches,
            "affected_tickets": row.affected_tickets or 0,
            "cost_per_breach_usd": cost_per_breach,
            "estimated_cost_usd": total_cost,
            "worst_breach_seconds": row.worst_breach_seconds or 0,
        }
    finally:
        db.close()


@router.get("/cost-per-queue")
async def cost_per_queue(days: int = Query(90, ge=1, le=365), _: User = Depends(require_admin)):
    """Cost per queue based on SLA breaches."""
    db = sync_session_factory()
    try:
        rows = db.execute(text("""
            SELECT t.queue, COUNT(*) as breaches, COUNT(DISTINCT t.id) as tickets
            FROM sla_metrics m JOIN tickets t ON t.id = m.ticket_id
            WHERE m.sla_breached = true AND m.created_at >= NOW() - INTERVAL ':days days'
            GROUP BY t.queue ORDER BY breaches DESC
        """.replace(":days", str(days)))).all()
        cost_per_breach = 50
        return {
            "queues": [{"queue": r.queue, "breaches": r.breaches, "tickets": r.tickets, "estimated_cost_usd": r.breaches * cost_per_breach} for r in rows],
            "total": len(rows),
        }
    finally:
        db.close()


@router.get("/forecast")
async def executive_forecast(days_ahead: int = Query(14, ge=1, le=90), _: User = Depends(get_current_user)):
    """Forecast SLA trends, overload, and risk."""
    db = sync_session_factory()
    try:
        row = db.execute(text("SELECT COUNT(*) as total, SUM(CASE WHEN sla_breached THEN 1 ELSE 0 END) as breached FROM sla_metrics")).first()
        total = row.total or 1
        breach_rate = (row.breached or 0) / total
        forecast_variance = 0.05
        return {
            "current_breach_rate": round(breach_rate * 100, 1),
            "forecast": [{"day": i + 1, "predicted_breach_rate": round(min(100, max(0, breach_rate * 100 + (i * forecast_variance * 100))), 1), "confidence": round(max(0, 95 - i * 3), 0)} for i in range(days_ahead)],
            "risk_level": "low" if breach_rate < 0.05 else "medium" if breach_rate < 0.15 else "high",
            "recommendation": "Текущий уровень SLA стабилен. Рекомендуется мониторинг очередей с повышенным риском.",
        }
    finally:
        db.close()


@router.get("/mttr")
async def mttr_analytics(days: int = Query(90, ge=1, le=365), queue: str | None = None, _: User = Depends(get_current_user)):
    """MTTR / MTTA analytics with trend."""
    db = sync_session_factory()
    try:
        q = "SELECT metric_name, AVG(metric_value_seconds) as avg_seconds, PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY metric_value_seconds) as median_seconds FROM sla_metrics WHERE created_at >= NOW() - INTERVAL ':days days'"
        params: dict[str, Any] = {}
        if queue:
            q += " AND ticket_id IN (SELECT id FROM tickets WHERE queue = :q)"
            params["q"] = queue
        q += " GROUP BY metric_name"
        rows = db.execute(text(q.replace(":days", str(days))), params).all()
        return {
            "metrics": [{"name": r.metric_name, "avg_seconds": round(r.avg_seconds or 0, 1), "avg_hours": round((r.avg_seconds or 0) / 3600, 2), "median_seconds": round(r.median_seconds or 0, 1), "median_hours": round((r.median_seconds or 0) / 3600, 2)} for r in rows],
        }
    finally:
        db.close()


@router.get("/efficiency-score")
async def operational_efficiency(days: int = Query(90, ge=1, le=365), _: User = Depends(get_current_user)):
    """Operational efficiency score (0-100)."""
    db = sync_session_factory()
    try:
        rows = db.execute(text("SELECT metric_name, AVG(efficiency_pct) as avg_eff FROM sla_efficiency WHERE created_at >= NOW() - INTERVAL ':days days' GROUP BY metric_name".replace(":days", str(days)))).all()
        scores = {r.metric_name: round(r.avg_eff or 100, 1) for r in rows}
        overall = round(sum(scores.values()) / max(len(scores), 1), 1) if scores else 100
        return {
            "score": overall,
            "by_metric": scores,
            "status": "excellent" if overall >= 95 else "good" if overall >= 85 else "needs_improvement",
        }
    finally:
        db.close()


@router.get("/compliance-trend")
async def compliance_trend(days: int = Query(90, ge=7, le=365), _: User = Depends(get_current_user)):
    """Daily compliance rate trend."""
    db = sync_session_factory()
    try:
        rows = db.execute(text("""
            SELECT DATE(created_at) as date,
                   COUNT(*) as total,
                   SUM(CASE WHEN sla_breached THEN 1 ELSE 0 END) as breached
            FROM sla_metrics
            WHERE created_at >= NOW() - INTERVAL ':days days'
            GROUP BY DATE(created_at) ORDER BY date
        """.replace(":days", str(days)))).all()
        return {
            "trend": [{"date": str(r.date), "total": r.total, "breached": r.breached, "compliance_pct": round((r.total - r.breached) / max(r.total, 1) * 100, 1)} for r in rows],
        }
    finally:
        db.close()
