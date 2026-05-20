"""AI Operations Copilot V2 — conversational analytics, AI dashboards, anomaly explanations, staffing forecasts."""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.database import sync_session_factory
from app.domain.models import SLAMetric, QueuePeriod, OwnershipPeriod, TicketSnapshot, TicketEvent

logger = logging.getLogger(__name__)


# === CONVERSATIONAL ANALYTICS (multi-turn support) ===

CONVERSATION_CONTEXT: dict[str, list[dict]] = {}
MAX_HISTORY = 10


def conversational_query(session_id: str, question: str) -> dict:
    """Handle multi-turn conversational analytics with context."""
    history = CONVERSATION_CONTEXT.get(session_id, [])
    history.append({"role": "user", "content": question, "timestamp": datetime.now(timezone.utc).isoformat()})
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]

    # Detect intent from question
    q = question.lower().strip()
    intent = _detect_intent(q)

    if intent == "explain_anomaly":
        answer = _explain_anomaly(q)
    elif intent == "staffing_forecast":
        answer = _staffing_forecast()
    elif intent == "queue_comparison":
        answer = _compare_queues(q)
    elif intent == "trend_explanation":
        answer = _explain_trend(q)
    elif intent == "mitigation":
        answer = _suggest_mitigation(q)
    elif intent == "dashboard_suggest":
        answer = _suggest_dashboard(q)
    else:
        # Fall back to basic copilot
        from app.services.ai.copilot import natural_query
        answer = natural_query(question)

    history.append({"role": "assistant", "content": answer.get("answer", str(answer)), "timestamp": datetime.now(timezone.utc).isoformat()})
    CONVERSATION_CONTEXT[session_id] = history

    return {
        "session_id": session_id,
        "answer": answer,
        "history_length": len(history),
    }


def _detect_intent(q: str) -> str:
    if any(w in q for w in ["аномал", "необыч", "отклон", "выброс", "всплеск"]):
        return "explain_anomaly"
    if any(w in q for w in ["прогноз", "нагрузк", "staff", "потреб"]):
        return "staffing_forecast"
    if any(w in q for w in ["сравн", "vs", "против", "разниц"]):
        return "queue_comparison"
    if any(w in q for w in ["тренд", "динамик", "изменен", "declin", "grow"]):
        return "trend_explanation"
    if any(w in q for w in ["исправ", "рекоменд", "mitig", "улучш", "предлож"]):
        return "mitigation"
    if any(w in q for w in ["дашборд", "dashboard", "покажи", "открой"]):
        return "dashboard_suggest"
    return "general"


def _explain_anomaly(question: str) -> dict:
    """Explain detected anomalies in natural language."""
    db = sync_session_factory()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=7)
        from app.services.ai.anomaly_detector import detect_anomalies
        anomalies = detect_anomalies(days=7)

        if not anomalies:
            return {"question": question, "answer": "Аномалий не обнаружено за последние 7 дней.", "category": "anomaly_explanation"}

        explanations = []
        for a in anomalies[:5]:
            sev = a.get("severity", "medium")
            sev_ru = {"critical": "Критическая", "high": "Высокая", "medium": "Средняя", "low": "Низкая"}
            explanations.append({
                "type": a.get("type", "unknown"),
                "severity": sev,
                "severity_ru": sev_ru.get(sev, sev),
                "detail": a.get("detail", ""),
                "queue": a.get("queue", ""),
                "impact": _estimate_anomaly_impact(a),
            })

        answer = f"Обнаружено {len(anomalies)} аномалий. "
        for e in explanations[:3]:
            answer += f"{e['severity_ru']}: {e['detail']} (очередь {e['queue']}). "

        return {"question": question, "answer": answer, "anomalies": explanations, "category": "anomaly_explanation"}
    finally:
        db.close()


def _estimate_anomaly_impact(anomaly: dict) -> str:
    atype = anomaly.get("type", "")
    if atype == "breach_spike":
        return "Высокое влияние на SLA — требуется немедленный анализ"
    if atype == "queue_saturation":
        return "Среднее влияние — снижение пропускной способности очереди"
    if atype == "high_reassignments":
        return "Среднее влияние — возможны проблемы с компетенциями"
    return "Низкое влияние"


def _staffing_forecast() -> dict:
    """Forecast staffing needs based on workload trends."""
    db = sync_session_factory()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=30)

        # Tickets per day trend
        daily_tickets = db.execute(
            text("""
                SELECT date_trunc('day', created_at) AS day, COUNT(*) AS tickets
                FROM ticket_snapshots
                WHERE created_at >= :since
                GROUP BY day ORDER BY day
            """),
            {"since": since},
        ).all()

        avg_daily = sum(r.tickets for r in daily_tickets) / max(len(daily_tickets), 1) if daily_tickets else 0

        # Current active tickets per owner
        owner_load = db.query(
            OwnershipPeriod.owner,
            func.count(func.distinct(OwnershipPeriod.ticket_id)).label("tickets"),
        ).filter(
            OwnershipPeriod.start_time >= since,
            OwnershipPeriod.end_time.is_(None),
        ).group_by(OwnershipPeriod.owner).all()

        overloaded = [r for r in owner_load if r.tickets > 20]
        underloaded = [r for r in owner_load if r.tickets < 5]

        # Suggest staffing
        needed_agents = max(1, int(avg_daily / 5))  # assume 5 tickets/agent/day

        return {
            "question": "Прогноз потребности в персонале",
            "answer": (
                f"Средняя дневная нагрузка: {avg_daily:.1f} тикетов. "
                f"Рекомендуемое число операторов: {needed_agents}. "
                f"Перегружены: {len(overloaded)} операторов. "
                f"Недозагружены: {len(underloaded)} операторов."
            ),
            "data": {
                "avg_daily_tickets": round(avg_daily, 1),
                "recommended_agents": needed_agents,
                "overloaded_agents": [{"name": r.owner, "tickets": r.tickets} for r in overloaded[:10]],
                "underloaded_agents": [{"name": r.owner, "tickets": r.tickets} for r in underloaded[:10]],
            },
            "category": "staffing_forecast",
        }
    finally:
        db.close()


def _compare_queues(question: str) -> dict:
    """Compare performance between queues."""
    db = sync_session_factory()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=30)
        rows = db.query(
            SLAMetric.queue_name,
            func.count(SLAMetric.id).label("total"),
            func.sum(SLAMetric.sla_breached.cast(int)).label("breaches"),
            func.avg(SLAMetric.metric_seconds).label("avg_seconds"),
        ).filter(
            SLAMetric.queue_name.isnot(None),
            SLAMetric.computed_at >= since,
        ).group_by(SLAMetric.queue_name).order_by(
            func.sum(SLAMetric.sla_breached.cast(int)).desc()
        ).all()

        queues = []
        for r in rows:
            rate = (r.breaches / max(r.total, 1)) * 100
            queues.append({
                "queue": r.queue_name,
                "breach_pct": round(rate, 2),
                "avg_seconds": round(float(r.avg_seconds), 2) if r.avg_seconds else 0,
                "total_metrics": r.total,
            })

        best = min(queues, key=lambda x: x["breach_pct"]) if queues else None
        worst = max(queues, key=lambda x: x["breach_pct"]) if queues else None

        answer = "Нет данных для сравнения."
        if best and worst:
            answer = (
                f"Лучшая очередь: {best['queue']} ({best['breach_pct']}% нарушений). "
                f"Худшая очередь: {worst['queue']} ({worst['breach_pct']}% нарушений). "
                f"Разница: {worst['breach_pct'] - best['breach_pct']:.1f}%."
            )

        return {"question": question, "answer": answer, "data": queues, "category": "queue_comparison"}
    finally:
        db.close()


def _explain_trend(question: str) -> dict:
    """Explain SLA trend with natural language."""
    from app.services.analytics.advanced_engine import analyze_trends
    trends = analyze_trends(days=90)

    degradation = trends.get("degradation_7d", {})
    delta = degradation.get("delta", 0)
    trend_word = "улучшается" if delta < -5 else "ухудшается" if delta > 5 else "стабилен"

    answer = (
        f"Тренд SLA за 90 дней: {trend_word}. "
        f"Изменение за последнюю неделю: {delta:+.1f}%. "
        f"Худший день: {trends.get('worst_day', {}).get('day', 'N/A')}. "
        f"Лучший день: {trends.get('best_day', {}).get('day', 'N/A')}."
    )

    return {"question": question, "answer": answer, "data": trends, "category": "trend_explanation"}


def _suggest_mitigation(question: str) -> dict:
    """Suggest mitigation actions based on current system state."""
    db = sync_session_factory()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=7)
        actions = []

        # Check overloaded queues
        q_rows = db.query(
            SLAMetric.queue_name,
            func.sum(SLAMetric.sla_breached.cast(int)).label("breaches"),
        ).filter(
            SLAMetric.queue_name.isnot(None),
            SLAMetric.computed_at >= since,
        ).group_by(SLAMetric.queue_name).order_by(
            func.sum(SLAMetric.sla_breached.cast(int)).desc()
        ).limit(5).all()

        for r in q_rows:
            if r.breaches > 10:
                actions.append({
                    "action": f"Перераспределить нагрузку в очереди {r.queue_name}",
                    "impact": "Высокий",
                    "effort": "Средний",
                })

        # Stalled tickets
        stalled = db.query(TicketSnapshot).filter(
            TicketSnapshot.is_closed == False,
            TicketSnapshot.created_at < datetime.now(timezone.utc) - timedelta(hours=48),
        ).count()
        if stalled > 10:
            actions.append({
                "action": f"Обработать {stalled} зависших тикетов",
                "impact": "Высокий",
                "effort": "Низкий",
            })

        if not actions:
            actions.append({
                "action": "Система в норме — активные действия не требуются",
                "impact": "Нет",
                "effort": "Нет",
            })

        return {
            "question": question,
            "answer": f"Предложено {len(actions)} действий по улучшению.",
            "actions": actions,
            "category": "mitigation",
        }
    finally:
        db.close()


def _suggest_dashboard(question: str) -> dict:
    """Suggest relevant dashboard based on question context."""
    q = question.lower()
    suggestions = []

    if any(w in q for w in ["sla", "наруш", "breach", "health"]):
        suggestions.append({"dashboard": "Executive", "url": "/dashboard/executive", "relevance": 0.95})
    if any(w in q for w in ["очеред", "queue", "нагрузк"]):
        suggestions.append({"dashboard": "Queue Performance", "url": "/dashboard/ops", "relevance": 0.9})
    if any(w in q for w in ["команд", "team", "agent", "сотруд"]):
        suggestions.append({"dashboard": "Team Dashboard", "url": "/dashboard/teams", "relevance": 0.85})
    if any(w in q for w in ["инцидент", "incident", "аварий"]):
        suggestions.append({"dashboard": "Incidents", "url": "/ops/incidents", "relevance": 0.9})
    if any(w in q for w in ["монитор", "real", "live"]):
        suggestions.append({"dashboard": "Wallboard", "url": "/wallboard", "relevance": 0.85})

    if not suggestions:
        suggestions.append({"dashboard": "Executive Dashboard", "url": "/dashboard/executive", "relevance": 1.0})

    return {
        "question": question,
        "answer": f"Рекомендованные дашборды: {', '.join(s['dashboard'] for s in suggestions)}.",
        "suggestions": suggestions,
        "category": "dashboard_suggestion",
    }


# === AI-GENERATED DASHBOARD ===

def generate_ai_dashboard(focus: str = "general") -> dict:
    """Generate an AI-recommended dashboard configuration."""
    db = sync_session_factory()
    try:
        dashboard = {
            "name": f"AI Dashboard — {focus}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "panels": [],
        }

        if focus == "breaches":
            dashboard["panels"] = [
                {"type": "timeseries", "title": "Breach Rate Trend", "metric": "breach_rate", "days": 30},
                {"type": "bar", "title": "Breaches by Queue", "metric": "breaches_by_queue", "days": 7},
                {"type": "table", "title": "Top Breached Tickets", "metric": "at_risk_tickets", "limit": 20},
                {"type": "stat", "title": "SLA Health Score", "metric": "health_score"},
            ]
        elif focus == "performance":
            dashboard["panels"] = [
                {"type": "timeseries", "title": "Response Time Trend", "metric": "avg_response_time", "days": 30},
                {"type": "timeseries", "title": "Resolution Time Trend", "metric": "avg_resolution_time", "days": 30},
                {"type": "bar", "title": "Queue Saturation", "metric": "queue_saturation"},
                {"type": "stat", "title": "MTTA", "metric": "mtta"},
                {"type": "stat", "title": "MTTR", "metric": "mttr"},
            ]
        else:
            dashboard["panels"] = [
                {"type": "stat", "title": "SLA Health Score", "metric": "health_score"},
                {"type": "stat", "title": "Active Tickets", "metric": "active_tickets"},
                {"type": "timeseries", "title": "Daily Breach Rate", "metric": "breach_rate", "days": 30},
                {"type": "bar", "title": "Top Queues by Breach Count", "metric": "breaches_by_queue", "days": 7},
                {"type": "table", "title": "At-Risk Tickets", "metric": "at_risk_tickets", "limit": 10},
                {"type": "stat", "title": "Avg Response Time", "metric": "avg_response_time"},
                {"type": "stat", "title": "Avg Resolution Time", "metric": "avg_resolution_time"},
            ]

        return dashboard
    finally:
        db.close()


def clear_conversation_history(session_id: str) -> None:
    """Clear conversation history for a session."""
    CONVERSATION_CONTEXT.pop(session_id, None)
