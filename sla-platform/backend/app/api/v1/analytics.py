"""Operational Intelligence analytics endpoints — trends, forecasting, correlations, cost analytics."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
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


# --- SLA Portal: daily breach trend ----------------------------------------
#
# Powers the "Тренд нарушений SLA" stacked-area chart on /sla/portal.
# Returns one row per day with separate `reaction` (response-time breaches)
# and `resolution` (resolution-time breaches) counts so the UI can render
# the canonical two-series chart (orange + violet).
#
# Filters:
#   scope: "all" | "support" | "infra" | "biz"  — matches queue name patterns
#          ("Support*", "Infrastructure*", everything-else respectively).
#   calendar: "all" | "24x7" | "bh"             — currently informational (SLA
#          definitions don't carry a calendar identifier yet); accepted so the
#          URL contract is stable for the frontend.
@router.get("/trend")
async def analytics_daily_trend(
    days: int = Query(30, ge=1, le=365),
    scope: Optional[str] = Query(None, description="all | support | infra | biz"),
    calendar: Optional[str] = Query(None, description="all | 24x7 | bh"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Daily breach-trend series for the SLA Portal main chart.

    Response shape:
        {
          "scope": {"days": 30, "scope": "all", "calendar": "all"},
          "daily": [
            { "date": "2026-05-01", "total": 120, "reaction": 14, "resolution": 9 },
            ...
          ]
        }
    """
    since = datetime.utcnow().date() - timedelta(days=days - 1)

    # Bucket sla_metrics by day + metric kind, count breaches. Scope filter
    # restricts queue_name via a LIKE pattern so the response matches the
    # scope-chip the analyst clicked.
    where_scope = ""
    if scope == "support":
        where_scope = "AND queue_name ILIKE 'Support%'"
    elif scope == "infra":
        where_scope = "AND queue_name ILIKE 'Infrastructure%'"
    elif scope == "biz":
        where_scope = "AND queue_name NOT ILIKE 'Support%' AND queue_name NOT ILIKE 'Infrastructure%'"

    sql = text(
        f"""
        SELECT
          DATE(computed_at) AS day,
          COUNT(*) AS total,
          COUNT(*) FILTER (
            WHERE sla_breached IS TRUE
              AND metric_name IN ('first_response_time','response_time','wall_response_time')
          ) AS reaction,
          COUNT(*) FILTER (
            WHERE sla_breached IS TRUE
              AND metric_name IN ('resolution_time','wall_resolution_time')
          ) AS resolution
        FROM sla_metrics
        WHERE computed_at >= :since
          {where_scope}
        GROUP BY day
        ORDER BY day ASC
        """
    )
    rows = (await db.execute(sql, {"since": since})).mappings().all()

    # Fill missing days with zeros so the chart always renders a contiguous
    # x-axis matching `days`.
    by_day = {r["day"].isoformat(): r for r in rows}
    daily = []
    for i in range(days):
        d = since + timedelta(days=i)
        key = d.isoformat()
        r = by_day.get(key)
        daily.append({
            "date": key,
            "total": int(r["total"]) if r else 0,
            "reaction": int(r["reaction"]) if r else 0,
            "resolution": int(r["resolution"]) if r else 0,
        })
    return {
        "scope": {"days": days, "scope": scope or "all", "calendar": calendar or "all"},
        "daily": daily,
    }


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
