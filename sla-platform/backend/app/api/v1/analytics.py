"""Operational Intelligence analytics endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.analytics.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/overview", response_model=dict)
async def analytics_overview(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    return await AnalyticsService.get_overview(db, days=days)


@router.get("/queue-heatmap", response_model=dict)
async def analytics_queue_heatmap(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    data = await AnalyticsService.get_queue_heatmap(db, days=days)
    return {"heatmap": data}


@router.get("/bottlenecks", response_model=dict)
async def analytics_bottlenecks(
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    data = await AnalyticsService.get_bottlenecks(db, days=days)
    return {"bottlenecks": data}


@router.get("/sla-risks", response_model=dict)
async def analytics_sla_risks(
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    data = await AnalyticsService.get_sla_risks(db, limit=limit)
    return {"risks": data}
