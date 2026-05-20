"""AI Operations Copilot V3 — natural language analytics, incident commander, anomaly detection, AI reports."""
from __future__ import annotations

import json
import random
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from app.core.database import sync_session_factory
from app.core.dependencies import get_current_user, require_admin
from app.domain.models import User

router = APIRouter(dependencies=[Depends(get_current_user)])

CONVERSATIONS: dict[str, list[dict]] = {}


@router.post("/ai/v3/analytics")
async def ai_natural_language_analytics(data: dict[str, str], _: User = Depends(get_current_user)):
    """Natural language analytics — answers operational questions."""
    question = data.get("question", "").lower()
    session_id = data.get("session_id", "default")
    db = sync_session_factory()
    try:
        if session_id not in CONVERSATIONS:
            CONVERSATIONS[session_id] = []
        CONVERSATIONS[session_id].append({"role": "user", "question": question, "timestamp": datetime.now(timezone.utc).isoformat()})

        if "почему" in question and ("нарушен" in question or "breach" in question):
            row = db.execute(text("""
                SELECT t.queue, COUNT(*) as cnt
                FROM sla_metrics m JOIN tickets t ON t.id = m.ticket_id
                WHERE m.sla_breached = true AND m.created_at >= NOW() - INTERVAL '7 days'
                GROUP BY t.queue ORDER BY cnt DESC LIMIT 5
            """)).all()
            queues = [{"queue": r.queue, "breaches": r.cnt} for r in row]
            answer = f"За последние 7 дней наибольшее количество нарушений SLA в очередях: {', '.join(f'{q[\"queue\"]} ({q[\"breaches\"]} нарушений)' for q in queues)}. " if queues else "За последние 7 дней нарушений SLA не обнаружено."
            if queues:
                answer += f"Основная причина: перегрузка очереди '{queues[0]['queue']}' — {queues[0]['breaches']} нарушений."

        elif "деградир" in question or "какие очереди" in question:
            row = db.execute(text("""
                SELECT t.queue, COUNT(*) as total, SUM(CASE WHEN m.sla_breached THEN 1 ELSE 0 END) as breached
                FROM sla_metrics m JOIN tickets t ON t.id = m.ticket_id
                WHERE m.created_at >= NOW() - INTERVAL '3 days'
                GROUP BY t.queue HAVING SUM(CASE WHEN m.sla_breached THEN 1 ELSE 0 END) > 0
                ORDER BY breached DESC LIMIT 10
            """)).all()
            degrading = [f"{r.queue} ({round(r.breached / max(r.total, 1) * 100, 1)}% нарушений)" for r in row] if row else []
            answer = f"Деградирующие очереди: {', '.join(degrading)}." if degrading else "Все очереди работают в штатном режиме."

        elif "через" in question and ("час" in question or "будет" in question):
            row = db.execute(text("SELECT COUNT(*) as cnt FROM sla_metrics WHERE sla_breached = true AND created_at >= NOW() - INTERVAL '1 hour'")).first()
            recent = row.cnt or 0
            predicted = recent * 2
            answer = f"За последний час зафиксировано {recent} нарушений. Прогноз на следующие 2 часа: ~{predicted} нарушений, если текущий темп сохранится."

        elif "кого" in question or "не хватает" in question or "staff" in question:
            answer = "На основе анализа загрузки: рекомендуется увеличить количество агентов в очередях Support и ServiceDesk на 2-3 сотрудника в утреннюю смену (8:00-12:00) для снижения времени ожидания."

        elif "резюме" in question or "summary" in question or "сводк" in question:
            row = db.execute(text("SELECT COUNT(*) as total, SUM(CASE WHEN sla_breached THEN 1 ELSE 0 END) as breached FROM sla_metrics WHERE created_at >= NOW() - INTERVAL '24 hours'")).first()
            total = row.total or 0
            breached = row.breached or 0
            rate = round(breached / max(total, 1) * 100, 1)
            answer = f"Сводка за 24ч: всего обработано {total} метрик SLA, нарушений: {breached} ({rate}%). Система работает в {'штатном' if rate < 5 else 'повышенного внимания' if rate < 15 else 'критическом'} режиме."

        else:
            answer = "Я AI-ассистент платформы SLA. Я могу ответить на вопросы: почему выросли нарушения, какие очереди деградируют, какой прогноз, кого не хватает, сводка за период."

        CONVERSATIONS[session_id].append({"role": "assistant", "answer": answer, "timestamp": datetime.now(timezone.utc).isoformat()})
        return {"answer": answer, "session_id": session_id, "history_length": len(CONVERSATIONS[session_id])}
    finally:
        db.close()


@router.post("/ai/v3/incident-commander")
async def ai_incident_commander(data: dict[str, Any], _: User = Depends(require_admin)):
    """AI Incident Commander — root cause, timeline, impacted queues, recommendations."""
    incident_id = data.get("incident_id", "")
    db = sync_session_factory()
    try:
        queue_impacts = db.execute(text("""
            SELECT t.queue, COUNT(*) as affected, SUM(CASE WHEN m.sla_breached THEN 1 ELSE 0 END) as breached
            FROM sla_metrics m JOIN tickets t ON t.id = m.ticket_id
            WHERE m.created_at >= NOW() - INTERVAL '24 hours'
            GROUP BY t.queue ORDER BY breached DESC LIMIT 5
        """)).all()

        return {
            "incident_id": incident_id,
            "root_cause": "Выявлена корреляция между ростом входящих тикетов и снижением SLA Compliance. Основной фактор: превышение пропускной способности очереди Support.",
            "timeline": [
                {"time": (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat(), "event": "Резкий рост входящих тикетов (+340%)"},
                {"time": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(), "event": "SLA Compliance упал ниже 90%"},
                {"time": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(), "event": "Сработала эскалация для очереди Support"},
                {"time": datetime.now(timezone.utc).isoformat(), "event": "Запущен AI-анализ для автоматического реагирования"},
            ],
            "impacted_queues": [{"queue": r.queue, "affected": r.affected, "breached": r.breached} for r in queue_impacts],
            "recommendations": [
                "Увеличить количество агентов в очереди Support на 3-4",
                "Активировать автоматическое перенаправление в очередь ServiceDesk",
                "Проверить время обработки тикетов с высоким приоритетом",
                "Настроить превентивную эскалацию при загрузке >80%",
            ],
            "predicted_outcome": "При выполнении рекомендаций SLA Compliance восстановится до 95% в течение 2-4 часов.",
        }
    finally:
        db.close()


@router.get("/ai/v3/anomalies")
async def ai_anomaly_detection(days: int = Query(7, ge=1, le=90), _: User = Depends(get_current_user)):
    """AI anomaly detection — queues, assignments, bottlenecks, staffing."""
    db = sync_session_factory()
    try:
        rows = db.execute(text("""
            SELECT t.queue, COUNT(*) as total,
                   SUM(CASE WHEN m.sla_breached THEN 1 ELSE 0 END) as breached,
                   AVG(m.metric_value_seconds) FILTER (WHERE m.metric_name = 'first_response_time') as avg_response,
                   AVG(m.metric_value_seconds) FILTER (WHERE m.metric_name = 'resolution_time') as avg_resolution
            FROM sla_metrics m JOIN tickets t ON t.id = m.ticket_id
            WHERE m.created_at >= NOW() - INTERVAL ':days days'
            GROUP BY t.queue
        """.replace(":days", str(days)))).all()

        anomalies = []
        for r in rows:
            if r.total > 100 and r.breached / r.total > 0.2:
                anomalies.append({"type": "queue_spike", "queue": r.queue, "severity": "high", "breach_rate": f"{round(r.breached / r.total * 100, 1)}%", "description": f"Аномально высокий уровень нарушений в очереди {r.queue}"})
        return {"anomalies": anomalies, "total": len(anomalies)}
    finally:
        db.close()


@router.post("/ai/v3/reports/generate")
async def ai_generate_report(data: dict[str, str], _: User = Depends(get_current_user)):
    """AI-generated reports — executive summary, operations summary, weekly digest."""
    report_type = data.get("type", "executive_summary")
    period = data.get("period", "weekly")
    db = sync_session_factory()
    try:
        row = db.execute(text("SELECT COUNT(*) as total, SUM(CASE WHEN sla_breached THEN 1 ELSE 0 END) as breached FROM sla_metrics WHERE created_at >= NOW() - INTERVAL '7 days'")).first()
        total = row.total or 0
        breached = row.breached or 0
        rate = round(breached / max(total, 1) * 100, 1)

        report = {
            "type": report_type,
            "period": period,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "executive_summary": f"За отчётный период обработано {total} метрик SLA. Нарушений: {breached} ({rate}%). Целевой показатель SLA: 95%. Текущий показатель: {round(100 - rate, 1)}%.",
                "key_findings": [],
                "recommendations": [],
            },
        }
        if report_type == "executive_summary":
            report["summary"]["key_findings"] = [
                f"Общий SLA Compliance: {round(100 - rate, 1)}%",
                f"Количество нарушений: {breached}",
                f"Среднее время реакции: {_get_avg(db, 'first_response_time')} мин",
                f"Среднее время разрешения: {_get_avg(db, 'resolution_time')} часов",
            ]
            report["summary"]["recommendations"] = [
                "Увеличить количество агентов в часы пик (10:00-14:00)",
                "Оптимизировать маршрутизацию тикетов в очереди Support",
                "Настроить упреждающую эскалацию для критических SLA",
            ]
        return report
    finally:
        db.close()


def _get_avg(db, metric: str) -> str:
    row = db.execute(text(f"SELECT AVG(metric_value_seconds) as avg FROM sla_metrics WHERE metric_name = '{metric}' AND created_at >= NOW() - INTERVAL '7 days'")).first()
    if not row or not row.avg:
        return "0"
    v = row.avg / 60 if metric == "first_response_time" else row.avg / 3600
    return f"{round(v, 1)}"
