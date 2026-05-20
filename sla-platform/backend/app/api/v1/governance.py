"""Advanced SLA Governance — rule builder, conflict detection, simulation, calendar, escalation."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from app.core.database import sync_session_factory
from app.core.dependencies import get_current_user, require_admin
from app.domain.models import User

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/governance/rules/conflicts")
async def detect_rule_conflicts(_: User = Depends(require_admin)):
    """Detect overlapping/missing queue rules."""
    db = sync_session_factory()
    try:
        rows = db.execute(text("SELECT id, name, queue_pattern, priority, response_target_seconds, resolution_target_seconds FROM sla_queue_rules WHERE is_active = true ORDER BY priority")).all()
        conflicts = []
        for i, a in enumerate(rows):
            for b in rows[i + 1:]:
                if a.queue_pattern == b.queue_pattern or (a.queue_pattern == "*" or b.queue_pattern == "*"):
                    conflicts.append({
                        "type": "overlap",
                        "rule_a": {"id": str(a.id), "name": a.name, "pattern": a.queue_pattern},
                        "rule_b": {"id": str(b.id), "name": b.name, "pattern": b.queue_pattern},
                        "description": f"'{a.name}' и '{b.name}' перекрываются по очереди '{a.queue_pattern}'",
                    })
        return {"conflicts": conflicts, "total": len(conflicts)}
    finally:
        db.close()


@router.post("/governance/simulate/bulk")
async def bulk_simulate(data: dict[str, Any], _: User = Depends(get_current_user)):
    """Simulate SLA impact of a rule change against real tickets."""
    queue = data.get("queue_name", "")
    response_target = data.get("response_target_seconds")
    resolution_target = data.get("resolution_target_seconds")
    db = sync_session_factory()
    try:
        query = "SELECT sla_breached, metric_name, metric_value_seconds FROM sla_metrics WHERE 1=1"
        params: dict = {}
        if queue:
            query += " AND ticket_id IN (SELECT id FROM tickets WHERE queue = :q)"
            params["q"] = queue
        rows = db.execute(text(query), params).all()

        response_breaches = 0
        resolution_breaches = 0
        total_response = 0
        total_resolution = 0

        for r in rows:
            if r.metric_name == "first_response_time" and response_target:
                total_response += 1
                if _is_breach(r.metric_value_seconds, response_target):
                    response_breaches += 1
            if r.metric_name == "resolution_time" and resolution_target:
                total_resolution += 1
                if _is_breach(r.metric_value_seconds, resolution_target):
                    resolution_breaches += 1

        return {
            "queue": queue,
            "response": {"target": response_target, "current_breaches": response_breaches, "total": total_response, "breach_rate": round(response_breaches / max(total_response, 1) * 100, 1)},
            "resolution": {"target": resolution_target, "current_breaches": resolution_breaches, "total": total_resolution, "breach_rate": round(resolution_breaches / max(total_resolution, 1) * 100, 1)},
        }
    finally:
        db.close()


def _is_breach(value: float | None, target: int) -> bool:
    if value is None:
        return False
    return value > target


@router.get("/governance/rules/graph")
async def rule_dependency_graph(_: User = Depends(require_admin)):
    """Build rule inheritance/priority graph."""
    db = sync_session_factory()
    try:
        rules = db.execute(text("SELECT id, name, queue_pattern, priority, parent_rule_id FROM sla_queue_rules WHERE is_active = true")).all()
        nodes = [{"id": str(r.id), "name": r.name, "pattern": r.queue_pattern, "priority": str(r.priority) if r.priority else "any"} for r in rules]
        edges = [{"source": str(r.parent_rule_id), "target": str(r.id)} for r in rules if r.parent_rule_id]
        return {"nodes": nodes, "edges": edges, "total": len(nodes)}
    finally:
        db.close()


@router.get("/governance/calendar/preview")
async def calendar_preview(calendar_id: str = Query(...), days: int = Query(30, ge=1, le=365), _: User = Depends(get_current_user)):
    """Preview a calendar's working hours for N days."""
    db = sync_session_factory()
    try:
        cal = db.execute(text("SELECT id, name, timezone, workdays, start_time, end_time, holidays_json, is_24x7 FROM sla_calendars WHERE id = :id"), {"id": calendar_id}).first()
        if not cal:
            raise HTTPException(404, "Calendar not found")
        holidays = json.loads(cal.holidays_json) if cal.holidays_json else []
        preview = []
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        for i in range(days):
            d = now + timedelta(days=i)
            day_name = d.strftime("%A").lower()[:3]
            is_working = cal.is_24x7 or day_name in (cal.workdays or [])
            is_holiday = d.strftime("%Y-%m-%d") in holidays
            preview.append({
                "date": d.strftime("%Y-%m-%d"),
                "day": d.strftime("%A"),
                "is_working": is_working and not is_holiday,
                "is_holiday": is_holiday,
                "hours": "00:00-24:00" if cal.is_24x7 else f"{cal.start_time}-{cal.end_time}",
            })
        return {"calendar": {"id": cal.id, "name": cal.name}, "preview": preview}
    finally:
        db.close()
