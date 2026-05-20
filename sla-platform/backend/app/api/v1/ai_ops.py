"""AI-powered operational intelligence API endpoints — Copilot, prediction, recommendations."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from app.core.dependencies import get_current_user
from app.domain.models import User

from app.services.ai.predictor import predict_breach_probability, predict_batch
from app.services.ai.anomaly_detector import detect_anomalies
from app.services.ai.staffing import get_staffing_recommendations
from app.services.ai.root_cause import generate_hints
from app.services.ai.incident_summary import generate_incident_summary
from app.services.ai.copilot import natural_query, generate_executive_summary, NL_QUERIES

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/predict/{ticket_id}")
async def predict_ticket(ticket_id: int, _: User = Depends(get_current_user)):
    result = predict_breach_probability(ticket_id)
    return {"prediction": result}


@router.post("/predict/batch")
async def predict_tickets(ticket_ids: list[int], _: User = Depends(get_current_user)):
    results = predict_batch(ticket_ids)
    return {"predictions": results}


@router.get("/anomalies")
async def get_anomalies(days: int = Query(7, ge=1, le=90), _: User = Depends(get_current_user)):
    anomalies = detect_anomalies(days)
    return {"anomalies": anomalies, "total": len(anomalies)}


@router.get("/staffing")
async def get_staffing(days: int = Query(30, ge=1, le=365), _: User = Depends(get_current_user)):
    recommendations = get_staffing_recommendations(days)
    return {"recommendations": recommendations}


@router.get("/hints")
async def get_hints(days: int = Query(7, ge=1, le=90), _: User = Depends(get_current_user)):
    hints = generate_hints(days)
    return {"hints": hints}


@router.post("/incident-summary")
async def incident_summary(data: dict[str, Any], _: User = Depends(get_current_user)):
    """Generate AI-powered summary for an incident with root causes and recommendations."""
    summary = generate_incident_summary(data)
    return {"summary": summary}


@router.post("/copilot/query")
async def copilot_query(data: dict[str, str], _: User = Depends(get_current_user)):
    """Natural language analytics query."""
    question = data.get("question", "")
    if not question:
        return {"error": "No question provided", "supported_queries": list(NL_QUERIES.values())}
    result = natural_query(question)
    return {"result": result}


@router.get("/copilot/queries")
async def copilot_supported_queries(_: User = Depends(get_current_user)):
    """List supported natural language queries."""
    return {"queries": NL_QUERIES}


@router.get("/executive-summary")
async def executive_summary(
    period: str = Query("daily", regex="^(daily|weekly|monthly)$"),
    _: User = Depends(get_current_user),
):
    """Generate executive summary report."""
    summary = generate_executive_summary(period)
    return {"summary": summary}
