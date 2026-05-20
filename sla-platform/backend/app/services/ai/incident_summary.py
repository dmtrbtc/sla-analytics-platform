"""AI incident summary — enriches incidents with predictive insights, root causes, and recommendations."""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from app.core.database import sync_session_factory
from app.domain.models import SLAMetric, QueuePeriod, TicketEvent, ImportSession
from app.services.ai.anomaly_detector import detect_anomalies
from app.services.ai.predictor import predict_breach_probability
from app.services.ai.root_cause import generate_hints
from app.services.ai.staffing import get_staffing_recommendations

logger = logging.getLogger(__name__)


def generate_incident_summary(incident: dict[str, Any]) -> dict[str, Any]:
    """Enrich an incident with AI-generated summary, root causes, and recommendations."""
    inc_type = incident.get("type", "")
    queue_name = incident.get("queue", "")
    severity = incident.get("severity", "medium")

    summary = _build_summary(inc_type, queue_name, severity)
    root_causes = _find_root_causes(inc_type, queue_name)
    recommendations = _generate_recommendations(inc_type, queue_name, severity)
    impact = _assess_impact(inc_type, queue_name)
    related = _find_related_incidents(inc_type, queue_name)

    return {
        "incident_id": incident.get("id", ""),
        "ai_summary": summary,
        "root_causes": root_causes,
        "recommendations": recommendations,
        "impact_assessment": impact,
        "related_incidents": related,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _build_summary(inc_type: str, queue_name: str, severity: str) -> str:
    templates = {
        "breach_spike": "Резкий рост нарушений SLA в очереди {queue}. Требуется немедленный анализ причин и корректирующие действия.",
        "queue_overload": "Очередь {queue} испытывает критическую нагрузку. Рекомендуется перераспределение ресурсов.",
        "high_reassignments": "Аномально высокий уровень переназначений в очереди {queue}. Возможны проблемы с компетенциями или процессами.",
        "stalled_queue": "Тикеты в очереди {queue} не обрабатываются более 48 часов. Требуется эскалация.",
        "import_failures": "Множественные сбои импорта данных. Проверьте доступность источников и формат данных.",
        "high_risk": "Накопление тикетов с высоким риском нарушения SLA в очереди {queue}.",
        "worker_down": "Отказ обработчика задач. Автоматическое восстановление запущено.",
    }
    template = templates.get(inc_type, f"Инцидент типа {inc_type} в очереди {queue_name}.")
    return template.format(queue=queue_name or "неопределенная очередь")


def _find_root_causes(inc_type: str, queue_name: str) -> list[dict[str, str]]:
    """Analyze root causes from available data."""
    causes = []
    db = sync_session_factory()
    try:
        since = datetime.now(timezone.utc) - timedelta(hours=24)

        if inc_type == "breach_spike":
            top_owner = db.query(
                SLAMetric.owner,
                SLAMetric.metric_name,
            ).filter(
                SLAMetric.sla_breached == True,
                SLAMetric.computed_at >= since,
            ).group_by(SLAMetric.owner, SLAMetric.metric_name).order_by(
                SLAMetric.sla_breached.desc()
            ).limit(3).all()
            for r in top_owner:
                causes.append({
                    "factor": f"Нарушения у {r.owner or 'неизвестный'} по метрике {r.metric_name}",
                    "confidence": "high",
                })

        elif inc_type == "queue_overload":
            visitors = db.query(
                TicketEvent.event_type,
                func.count(TicketEvent.id).label("cnt"),
            ).filter(
                TicketEvent.queue_name == queue_name if queue_name else True,
                TicketEvent.event_time >= since,
            ).group_by(TicketEvent.event_type).order_by(
                func.count(TicketEvent.id).desc()
            ).limit(5).all()
            for r in visitors:
                causes.append({
                    "factor": f"{r.cnt} событий типа {r.event_type}",
                    "confidence": "medium",
                })

        if not causes:
            hints = generate_hints(days=1)
            queue_hints = [h for h in hints if not queue_name or queue_name in h.get("message", "")]
            for h in queue_hints[:3]:
                causes.append({
                    "factor": h.get("message", ""),
                    "confidence": "medium",
                })

    except Exception as exc:
        logger.warning("Root cause analysis failed: %s", exc)
        causes.append({"factor": "Не удалось выполнить анализ", "confidence": "low"})
    finally:
        db.close()

    return causes if causes else [{"factor": "Автоматический анализ не выявил явных причин", "confidence": "low"}]


def _generate_recommendations(inc_type: str, queue_name: str, severity: str) -> list[dict[str, str]]:
    """Generate actionable recommendations."""
    recommendations = []

    if inc_type in ("breach_spike", "queue_overload"):
        recommendations.append({
            "action": "Перераспределить тикеты между операторами",
            "priority": "high" if severity in ("critical", "high") else "medium",
            "expected_impact": "Снижение нагрузки на очередь на 30-50%",
        })
        recommendations.append({
            "action": "Провести анализ SLA-правил для очереди",
            "priority": "medium",
            "expected_impact": "Оптимизация целевых показателей",
        })

    if inc_type == "high_reassignments":
        recommendations.append({
            "action": "Провести аудит компетенций операторов очереди",
            "priority": "high",
            "expected_impact": "Снижение переназначений на 40-60%",
        })

    if inc_type == "import_failures":
        recommendations.append({
            "action": "Проверить подключение к источникам данных",
            "priority": "critical",
            "expected_impact": "Восстановление импорта",
        })

    # Check staffing recommendations
    try:
        staffing = get_staffing_recommendations(days=30)
        for s in staffing[:2]:
            if queue_name and ("queue" not in s or queue_name in str(s)):
                recommendations.append({
                    "action": s.get("recommendation", ""),
                    "priority": "medium",
                    "expected_impact": s.get("rationale", ""),
                })
    except Exception:
        pass

    return recommendations


def _assess_impact(inc_type: str, queue_name: str) -> dict[str, Any]:
    """Assess business impact of the incident."""
    db = sync_session_factory()
    try:
        since = datetime.now(timezone.utc) - timedelta(hours=24)

        affected_tickets = 0
        if queue_name:
            affected_tickets = db.query(func.count(func.distinct(SLAMetric.ticket_id))).filter(
                SLAMetric.queue_name == queue_name,
                SLAMetric.computed_at >= since,
            ).scalar() or 0

        return {
            "affected_tickets_24h": affected_tickets,
            "severity": inc_type,
            "business_impact": "high" if affected_tickets > 50 else "medium" if affected_tickets > 10 else "low",
        }
    except Exception:
        return {"affected_tickets_24h": 0, "severity": inc_type, "business_impact": "unknown"}
    finally:
        db.close()


def _find_related_incidents(inc_type: str, queue_name: str) -> list[dict[str, str]]:
    """Find related active incidents from in-memory store."""
    try:
        from app.api.v1.incidents import _incidents

        related = []
        for iid, inc in _incidents.items():
            if inc.get("status") == "resolved":
                continue
            if inc.get("id") == inc.get("id"):
                continue
            if inc.get("queue") == queue_name or inc.get("type") == inc_type:
                related.append({
                    "id": iid,
                    "type": inc.get("type", ""),
                    "severity": inc.get("severity", ""),
                    "title": inc.get("title", ""),
                })
        return related[:5]
    except Exception:
        return []
