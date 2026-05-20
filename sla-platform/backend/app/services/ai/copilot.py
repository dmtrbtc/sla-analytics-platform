"""AI Copilot — natural language analytics, root cause engine, recommendations, executive summaries."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.database import sync_session_factory
from app.domain.models import SLAMetric, QueuePeriod, TicketEvent, OwnershipPeriod, TicketSnapshot

logger = logging.getLogger(__name__)

# === NATURAL LANGUAGE ANALYTICS ===

NL_QUERIES: dict[str, str] = {
    "why_breach_spike": "Почему выросли нарушения SLA",
    "worst_queues": "Какие очереди самые проблемные",
    "overloaded_agents": "Какие сотрудники перегружены",
    "what_degraded_sla": "Что ухудшило SLA вчера",
    "trend_this_month": "Тренд SLA за месяц",
    "breach_root_causes": "Основные причины нарушений",
    "stalled_tickets": "Зависшие тикеты",
    "recommendations": "Рекомендации по улучшению",
}


def natural_query(question: str) -> dict:
    """Process a natural language analytics question."""
    q = question.lower().strip()

    if any(w in q for w in ["выросл", "нарушен", "breach", "spike"]):
        return _answer_why_breach_spike()
    if any(w in q for w in ["проблемн", "худш", "worst", "плох"]):
        return _answer_worst_queues()
    if any(w in q for w in ["перегруж", "загруж", "staff", "overload"]):
        return _answer_overloaded_agents()
    if any(w in q for w in ["ухудш", "вчера", "degrad"]):
        return _answer_degraded_sla()
    if any(w in q for w in ["тренд", "месяц", "trend"]):
        return _answer_trend()
    if any(w in q for w in ["причин", "root", "cause"]):
        return _answer_root_causes()
    if any(w in q for w in ["завис", "stall", "aged", "стары"]):
        return _answer_stalled_tickets()
    if any(w in q for w in ["рекоменд", "лучш", "improve", "предлож"]):
        return _answer_recommendations()

    return {
        "question": question,
        "answer": "Я не смог определить тип вопроса. Попробуйте: 'Почему выросли нарушения SLA?', 'Какие очереди самые проблемные?', 'Какие сотрудники перегружены?', 'Что ухудшило SLA вчера?'",
        "category": "unknown",
    }


def _answer_why_breach_spike() -> dict:
    db = sync_session_factory()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=7)
        now = since + timedelta(days=7)

        # Breach rate now vs last period
        recent = db.query(
            func.count(SLAMetric.id).label("total"),
            func.sum(SLAMetric.sla_breached.cast(int)).label("breaches"),
        ).filter(SLAMetric.computed_at >= now - timedelta(days=1)).first()

        previous = db.query(
            func.count(SLAMetric.id).label("total"),
            func.sum(SLAMetric.sla_breached.cast(int)).label("breaches"),
        ).filter(
            SLAMetric.computed_at >= now - timedelta(days=3),
            SLAMetric.computed_at < now - timedelta(days=1),
        ).first()

        recent_rate = (recent.breaches / max(recent.total, 1)) * 100 if recent else 0
        prev_rate = (previous.breaches / max(previous.total, 1)) * 100 if previous else 0

        # Top breached queues
        top_queues = db.query(
            SLAMetric.queue_name,
            func.count(SLAMetric.id).label("breaches"),
        ).filter(
            SLAMetric.sla_breached == True,
            SLAMetric.computed_at >= now - timedelta(days=1),
        ).group_by(SLAMetric.queue_name).order_by(func.count(SLAMetric.id).desc()).limit(5).all()

        queues_str = ", ".join([f"{r.queue_name} ({r.breaches})" for r in top_queues])

        delta = recent_rate - prev_rate
        direction = "вырос" if delta > 0 else "снизился"

        return {
            "question": "Почему выросли нарушения SLA?",
            "answer": f"Уровень нарушений {direction} с {prev_rate:.1f}% до {recent_rate:.1f}% за последние сутки. "
                      f"Наиболее проблемные очереди: {queues_str or 'нет данных'}.",
            "data": {
                "recent_breach_pct": round(recent_rate, 2),
                "previous_breach_pct": round(prev_rate, 2),
                "delta_pct": round(delta, 2),
                "top_breached_queues": [{"queue": r.queue_name, "breaches": r.breaches} for r in top_queues],
            },
            "category": "breach_analysis",
        }
    finally:
        db.close()


def _answer_worst_queues() -> dict:
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
        ).limit(10).all()

        queues = []
        for r in rows:
            rate = (r.breaches / max(r.total, 1)) * 100
            queues.append({
                "queue": r.queue_name,
                "breach_pct": round(rate, 2),
                "total_metrics": r.total,
                "breaches": r.breaches,
                "avg_seconds": round(float(r.avg_seconds), 2) if r.avg_seconds else 0,
            })

        worst = queues[0] if queues else None
        answer = "Нет данных по очередям."
        if worst:
            answer = f"Худшая очередь: {worst['queue']} с {worst['breach_pct']}% нарушений. " \
                     f"Топ-5 проблемных: {', '.join([q['queue'] + ' (' + str(q['breach_pct']) + '%)' for q in queues[:5]])}."

        return {"question": "Какие очереди самые проблемные?", "answer": answer, "data": queues, "category": "queue_analysis"}
    finally:
        db.close()


def _answer_overloaded_agents() -> dict:
    db = sync_session_factory()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=7)
        rows = db.query(
            OwnershipPeriod.owner,
            func.count(func.distinct(OwnershipPeriod.ticket_id)).label("tickets"),
        ).filter(
            OwnershipPeriod.owner.isnot(None),
            OwnershipPeriod.start_time >= since,
        ).group_by(OwnershipPeriod.owner).order_by(
            func.count(func.distinct(OwnershipPeriod.ticket_id)).desc()
        ).limit(10).all()

        agents = [{"name": r.owner, "tickets": r.tickets} for r in rows]
        overloaded = [a for a in agents if a["tickets"] > 20]

        if overloaded:
            names = ", ".join([f"{a['name']} ({a['tickets']} тикетов)" for a in overloaded[:5]])
            answer = f"Перегруженные сотрудники: {names}. Рекомендуется перераспределение."
        else:
            answer = "Критической перегрузки сотрудников не обнаружено."

        return {"question": "Какие сотрудники перегружены?", "answer": answer, "data": agents, "category": "workload"}
    finally:
        db.close()


def _answer_degraded_sla() -> dict:
    db = sync_session_factory()
    try:
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        day_before = yesterday - timedelta(days=1)

        yest = db.query(
            func.count(SLAMetric.id).label("total"),
            func.sum(SLAMetric.sla_breached.cast(int)).label("breaches"),
        ).filter(
            SLAMetric.computed_at >= yesterday,
            SLAMetric.computed_at < yesterday + timedelta(days=1),
        ).first()

        prev = db.query(
            func.count(SLAMetric.id).label("total"),
            func.sum(SLAMetric.sla_breached.cast(int)).label("breaches"),
        ).filter(
            SLAMetric.computed_at >= day_before,
            SLAMetric.computed_at < yesterday,
        ).first()

        yest_rate = (yest.breaches / max(yest.total, 1)) * 100 if yest else 0
        prev_rate = (prev.breaches / max(prev.total, 1)) * 100 if prev else 0

        delta = yest_rate - prev_rate
        if delta > 5:
            answer = f"SLA ухудшилось на {delta:.1f}% (было {prev_rate:.1f}%, стало {yest_rate:.1f}%)."
        elif delta < -5:
            answer = f"SLA улучшилось на {abs(delta):.1f}% (было {prev_rate:.1f}%, стало {yest_rate:.1f}%)."
        else:
            answer = f"SLA стабильно: {yest_rate:.1f}% нарушений (изменение {delta:+.1f}%)."

        return {"question": "Что ухудшило SLA вчера?", "answer": answer, "data": {
            "yesterday_breach_pct": round(yest_rate, 2),
            "previous_breach_pct": round(prev_rate, 2),
            "delta": round(delta, 2),
        }, "category": "degradation"}
    finally:
        db.close()


def _answer_trend() -> dict:
    db = sync_session_factory()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=30)
        rows = db.execute(
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

        daily = []
        for r in rows:
            rate = (r.breaches / max(r.total, 1)) * 100
            daily.append({"date": str(r.day.date()), "breach_pct": round(rate, 2)})

        if len(daily) >= 2:
            first = daily[0]["breach_pct"]
            last = daily[-1]["breach_pct"]
            trend = "улучшение" if last < first else "ухудшение" if last > first else "стабильно"
            answer = f"За месяц тренд: {trend}. Было {first}%, стало {last}%."
        else:
            answer = "Недостаточно данных для тренда."

        return {"question": "Тренд SLA за месяц", "answer": answer, "data": daily, "category": "trend"}
    finally:
        db.close()


def _answer_root_causes() -> dict:
    db = sync_session_factory()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=7)
        rows = db.query(
            SLAMetric.queue_name,
            SLAMetric.owner,
            func.count(SLAMetric.id).label("breaches"),
        ).filter(
            SLAMetric.sla_breached == True,
            SLAMetric.computed_at >= since,
        ).group_by(SLAMetric.queue_name, SLAMetric.owner).order_by(
            func.count(SLAMetric.id).desc()
        ).limit(10).all()

        causes = [{"queue": r.queue_name, "owner": r.owner, "breaches": r.breaches} for r in rows]
        top = causes[0] if causes else None
        answer = "Нет данных о нарушениях."
        if top:
            answer = f"Основная причина нарушений: очередь {top['queue']}, ответственный {top['owner'] or 'неизвестен'} ({top['breaches']} нарушений)."

        return {"question": "Основные причины нарушений", "answer": answer, "data": causes, "category": "root_cause"}
    finally:
        db.close()


def _answer_stalled_tickets() -> dict:
    db = sync_session_factory()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        rows = db.query(TicketSnapshot).filter(
            TicketSnapshot.is_closed == False,
            TicketSnapshot.created_at < cutoff,
        ).order_by(TicketSnapshot.created_at.asc()).limit(20).all()

        tickets = [{"ticket_id": t.ticket_id, "ticket_number": t.ticket_number, "queue": t.current_queue, "owner": t.current_owner, "created_at": str(t.created_at)} for t in rows]

        if tickets:
            answer = f"Обнаружено {len(tickets)} зависших тикетов (более 48ч без движения). Старейший: #{tickets[0]['ticket_number']} в очереди {tickets[0]['queue']}."
        else:
            answer = "Зависших тикетов не обнаружено."

        return {"question": "Зависшие тикеты", "answer": answer, "data": tickets, "category": "stalled"}
    finally:
        db.close()


def _answer_recommendations() -> dict:
    db = sync_session_factory()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=7)
        recs = []

        # Overloaded queues
        q_rows = db.query(
            SLAMetric.queue_name,
            func.count(SLAMetric.id).label("total"),
            func.sum(SLAMetric.sla_breached.cast(int)).label("breaches"),
        ).filter(
            SLAMetric.queue_name.isnot(None),
            SLAMetric.computed_at >= since,
        ).group_by(SLAMetric.queue_name).having(
            (func.sum(SLAMetric.sla_breached.cast(int)) * 1.0 / func.nullif(func.count(SLAMetric.id), 0)) > 0.2
        ).all()
        for r in q_rows:
            recs.append({
                "type": "queue_overload",
                "queue": r.queue_name,
                "recommendation": f"Перераспределить нагрузку в очереди {r.queue_name} ({r.breaches}/{r.total} нарушений)",
                "priority": "high",
            })

        # Overloaded agents
        a_rows = db.query(
            OwnershipPeriod.owner,
            func.count(func.distinct(OwnershipPeriod.ticket_id)).label("tickets"),
        ).filter(
            OwnershipPeriod.start_time >= since,
        ).group_by(OwnershipPeriod.owner).having(
            func.count(func.distinct(OwnershipPeriod.ticket_id)) > 20
        ).order_by(func.count(func.distinct(OwnershipPeriod.ticket_id)).desc()).limit(10).all()
        for r in a_rows:
            recs.append({
                "type": "agent_overload",
                "agent": r.owner,
                "recommendation": f"Снизить нагрузку на {r.owner}: {r.tickets} тикетов за неделю",
                "priority": "medium",
            })

        # Stalled
        stalled = db.query(TicketSnapshot).filter(
            TicketSnapshot.is_closed == False,
            TicketSnapshot.created_at < datetime.now(timezone.utc) - timedelta(hours=48),
        ).count()
        if stalled > 10:
            recs.append({
                "type": "stalled_tickets",
                "recommendation": f"Обработать {stalled} зависших тикетов (старше 48ч)",
                "priority": "high",
            })

        answer = f"Сгенерировано {len(recs)} рекомендаций." if recs else "Система в норме, рекомендаций нет."
        return {"question": "Рекомендации по улучшению", "answer": answer, "data": recs, "category": "recommendations"}
    finally:
        db.close()


# === EXECUTIVE SUMMARY ===

def generate_executive_summary(period: str = "daily") -> dict:
    """Generate an executive summary report."""
    db = sync_session_factory()
    try:
        now = datetime.now(timezone.utc)
        if period == "daily":
            since = now - timedelta(days=1)
            label = "ежедневный"
        elif period == "weekly":
            since = now - timedelta(days=7)
            label = "еженедельный"
        else:
            since = now - timedelta(days=30)
            label = "ежемесячный"

        # SLA health score
        total_metrics = db.query(func.count(SLAMetric.id)).filter(SLAMetric.computed_at >= since).scalar() or 1
        total_breaches = db.query(func.count(SLAMetric.id)).filter(SLAMetric.sla_breached == True, SLAMetric.computed_at >= since).scalar() or 0
        health_score = round((1 - total_breaches / total_metrics) * 100, 2)

        # Key metrics
        avg_response = db.query(func.avg(SLAMetric.metric_seconds)).filter(
            SLAMetric.metric_name == "first_response_time",
            SLAMetric.computed_at >= since,
        ).scalar() or 0
        avg_resolution = db.query(func.avg(SLAMetric.metric_seconds)).filter(
            SLAMetric.metric_name == "resolution_time",
            SLAMetric.computed_at >= since,
        ).scalar() or 0

        # Top issues
        top_queue = db.query(
            SLAMetric.queue_name,
            func.sum(SLAMetric.sla_breached.cast(int)).label("breaches"),
        ).filter(
            SLAMetric.queue_name.isnot(None),
            SLAMetric.computed_at >= since,
        ).group_by(SLAMetric.queue_name).order_by(
            func.sum(SLAMetric.sla_breached.cast(int)).desc()
        ).first()

        # At-risk tickets
        at_risk = db.query(func.count(func.distinct(SLAMetric.ticket_id))).filter(
            SLAMetric.sla_breached == False,
            SLAMetric.risk_level.in_(["high", "critical"]),
            SLAMetric.computed_at >= since,
        ).scalar() or 0

        return {
            "period": period,
            "generated_at": now.isoformat(),
            "title": f"{label.title()} отчет SLA Intelligence",
            "sla_health_score": health_score,
            "total_metrics_analyzed": total_metrics,
            "total_breaches": total_breaches,
            "breach_rate_pct": round(total_breaches / total_metrics * 100, 2),
            "avg_response_time_seconds": round(float(avg_response), 2),
            "avg_response_time_hours": round(float(avg_response) / 3600, 2),
            "avg_resolution_time_hours": round(float(avg_resolution) / 3600, 2),
            "tickets_at_risk": at_risk,
            "worst_queue": top_queue[0] if top_queue else None,
            "key_insights": _generate_insights(health_score, total_breaches, total_metrics, at_risk, avg_response, avg_resolution),
        }
    finally:
        db.close()


def _generate_insights(health_score: float, breaches: int, total: int, at_risk: int, avg_resp: float, avg_res: float) -> list[str]:
    insights = []
    if health_score > 95:
        insights.append("Отличное состояние SLA — платформа работает эффективно.")
    elif health_score > 80:
        insights.append("Хорошее состояние SLA — требуется мониторинг проблемных очередей.")
    else:
        insights.append("Требуется внимание: уровень SLA ниже целевых показателей.")

    if at_risk > 10:
        insights.append(f"Обнаружено {at_risk} тикетов с высоким риском нарушения SLA.") if at_risk > 0 else None
    if avg_resp / 3600 > 4:
        insights.append(f"Среднее время ответа ({avg_resp/3600:.1f}ч) превышает целевые показатели.")
    return insights
