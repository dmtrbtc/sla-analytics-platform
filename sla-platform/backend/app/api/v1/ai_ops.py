"""AI-powered operational intelligence API endpoints."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from app.core.dependencies import get_current_user
from app.domain.models import User

from app.services.ai.predictor import predict_breach_probability, predict_batch
from app.services.ai.anomaly_detector import detect_anomalies
from app.services.ai.staffing import get_staffing_recommendations
from app.services.ai.root_cause import generate_hints

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
