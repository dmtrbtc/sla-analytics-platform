"""Operational Intelligence analytics endpoints — trends, forecasting, correlations, cost analytics."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.analytics.analytics_service import AnalyticsService
from app.services.analytics.advanced_analytics import AdvancedAnalytics
from app.services.analytics.advanced_engine import analyze_trends, forecast_breaches, queue_saturation_forecast, find_correlations, estimate_sla_costs
from app.services.analytics.materialized_view_service import check_view_staleness, refresh_all_views

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


@router.get("/trends")
async def analytics_trends(days: int = Query(90, ge=7, le=365)):
    data = analyze_trends(days=days)
    return {"trends": data}


@router.get("/forecast")
async def analytics_forecast(days_ahead: int = Query(14, ge=1, le=90)):
    data = forecast_breaches(days_ahead=days_ahead)
    return {"forecast": data}


@router.get("/queue-saturation")
async def analytics_queue_saturation(days_ahead: int = Query(7, ge=1, le=30)):
    data = queue_saturation_forecast(days_ahead=days_ahead)
    return {"saturation": data}


@router.get("/correlations")
async def analytics_correlations():
    data = find_correlations()
    return {"correlations": data}


@router.get("/costs")
async def analytics_costs():
    data = estimate_sla_costs()
    return {"costs": data}


@router.get("/materialized-views/status")
async def materialized_view_status():
    from app.core.database import sync_session_factory
    db = sync_session_factory()
    try:
        status = check_view_staleness(db)
        return {"views": status}
    finally:
        db.close()


@router.post("/materialized-views/refresh")
async def materialized_view_refresh():
    from app.core.database import sync_session_factory
    db = sync_session_factory()
    try:
        results = refresh_all_views(db, concurrently=True)
        return {"results": results}
    finally:
        db.close()
