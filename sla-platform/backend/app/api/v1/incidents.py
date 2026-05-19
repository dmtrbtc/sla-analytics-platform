"""Incident management API — detection, tracking, resolution."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, and_
from app.core.dependencies import get_current_user, get_db
from app.domain.models import User
from app.domain.models import SLAMetric, QueuePeriod, TicketEvent, ImportSession
from app.core.database import sync_session_factory
from app.services.ai.anomaly_detector import detect_anomalies
from app.core.events import publish_event_sync, CHANNEL_OPS, EVENT_INCIDENT_CREATED, EVENT_INCIDENT_RESOLVED

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])

# In-memory incident store (would use DB in production)
_incidents: dict[str, dict[str, Any]] = {}
_comments: dict[str, list[dict[str, Any]]] = {}

INCIDENT_SEVERITY_COLORS = {"critical": "red", "high": "orange", "medium": "gold", "low": "green"}

INCIDENT_TYPES = {
    "breach_spike": "Всплеск нарушений",
    "queue_overload": "Перегрузка очереди",
    "high_reassignments": "Аномальные переназначения",
    "stalled_queue": "Зависшие тикеты",
    "import_failures": "Сбои импорта",
    "high_risk": "Накопление рисков",
    "worker_down": "Отказ воркера",
}


def _auto_detect_incidents() -> list[dict[str, Any]]:
    """Auto-detect incidents from anomaly data and system metrics."""
    incidents = []
    db = sync_session_factory()
    try:
        # Check anomaly detectors
        anomalies = detect_anomalies(days=1)
        for a in anomalies:
            if a.get("severity") in ("critical", "high"):
                incidents.append({
                    "type": a.get("type", "unknown"),
                    "severity": a.get("severity", "medium"),
                    "title": INCIDENT_TYPES.get(a.get("type", ""), a.get("type", "Неизвестно")),
                    "summary": a.get("detail", ""),
                    "queue": a.get("queue", ""),
                    "source": "anomaly_detector",
                })

        # Check import failures in last 24h
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        failed_imports = db.query(func.count(ImportSession.id)).filter(
            ImportSession.status == "failed",
            ImportSession.created_at >= since,
        ).scalar() or 0
        if failed_imports >= 3:
            incidents.append({
                "type": "import_failures",
                "severity": "high",
                "title": "Множественные сбои импорта",
                "summary": f"{failed_imports} сбоев импорта за последние 24 часа",
                "queue": "",
                "source": "system_monitor",
            })

        # Check high SLA breach rate in last hour
        since_h = datetime.now(timezone.utc) - timedelta(hours=1)
        breach_rate_row = db.query(
            func.count(SLAMetric.id).label("total"),
            func.sum(SLAMetric.sla_breached.cast(int)).label("breaches"),
        ).filter(SLAMetric.computed_at >= since_h).first()

        if breach_rate_row and breach_rate_row.total > 0:
            rate = breach_rate_row.breaches / breach_rate_row.total
            if rate > 0.3:
                incidents.append({
                    "type": "breach_spike",
                    "severity": "high",
                    "title": "Критический рост нарушений SLA",
                    "summary": f"{rate:.0%} нарушений за последний час",
                    "queue": "",
                    "source": "system_monitor",
                })

        return incidents
    finally:
        db.close()


@router.get("/incidents/detect")
async def detect_incidents(_: User = Depends(get_current_user)):
    """Auto-detect and return new incidents without persisting."""
    incidents = _auto_detect_incidents()
    return {"incidents": incidents, "total": len(incidents)}


@router.get("/incidents")
async def list_incidents(
    status: Optional[str] = Query(None, regex="^(active|resolved)$"),
    severity: Optional[str] = Query(None, regex="^(critical|high|medium|low)$"),
    _: User = Depends(get_current_user),
):
    result = []
    for iid, inc in _incidents.items():
        if status and inc.get("status") != status:
            continue
        if severity and inc.get("severity") != severity:
            continue
        result.append({"id": iid, **inc})
    return {"incidents": sorted(result, key=lambda x: x.get("created_at", ""), reverse=True), "total": len(result)}


@router.post("/incidents")
async def create_incident(data: dict[str, Any], _: User = Depends(get_current_user)):
    iid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    _incidents[iid] = {
        **data,
        "id": iid,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    _comments[iid] = []
    # Publish event
    publish_event_sync(CHANNEL_OPS, EVENT_INCIDENT_CREATED, {"incident_id": iid, **data})
    return {"incident": {"id": iid, **_incidents[iid]}}


@router.get("/incidents/{incident_id}")
async def get_incident(incident_id: str, _: User = Depends(get_current_user)):
    inc = _incidents.get(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"incident": inc, "comments": _comments.get(incident_id, [])}


@router.post("/incidents/{incident_id}/acknowledge")
async def acknowledge_incident(incident_id: str, _: User = Depends(get_current_user)):
    inc = _incidents.get(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    inc["status"] = "acknowledged"
    inc["updated_at"] = datetime.now(timezone.utc).isoformat()
    return {"incident": inc}


@router.post("/incidents/{incident_id}/resolve")
async def resolve_incident(incident_id: str, data: Optional[dict] = None, _: User = Depends(get_current_user)):
    inc = _incidents.get(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    resolution = (data or {}).get("resolution", "Resolved manually")
    inc["status"] = "resolved"
    inc["resolution"] = resolution
    inc["resolved_at"] = datetime.now(timezone.utc).isoformat()
    inc["updated_at"] = datetime.now(timezone.utc).isoformat()
    publish_event_sync(CHANNEL_OPS, EVENT_INCIDENT_RESOLVED, {"incident_id": incident_id, "resolution": resolution})
    return {"incident": inc}


@router.post("/incidents/{incident_id}/comments")
async def add_comment(incident_id: str, data: dict[str, str], _: User = Depends(get_current_user)):
    if incident_id not in _incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    comment = {
        "id": str(uuid.uuid4()),
        "text": data.get("text", ""),
        "author": data.get("author", "unknown"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _comments.setdefault(incident_id, []).append(comment)
    return {"comment": comment}
