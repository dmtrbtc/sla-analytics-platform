"""Observability V3 — system diagnostics, health check, distributed tracing endpoints."""
from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user
from app.core.tracing import get_recent_traces, get_sql_traces, tracer
from app.domain.models import User
from app.services.diagnostics import get_full_diagnostics, get_live_health

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/health")
async def live_health():
    return get_live_health()


@router.get("/diagnostics")
async def system_diagnostics(_: User = Depends(get_current_user)):
    return get_full_diagnostics()


@router.get("/traces")
async def distributed_traces(
    limit: int = Query(100, le=1000),
    trace_id: str = Query(None),
    _: User = Depends(get_current_user),
):
    if trace_id:
        spans = [s for s in tracer.get_traces(limit=10000) if s.get("trace_id") == trace_id]
    else:
        spans = get_recent_traces(limit=limit)
    return {"traces": spans, "total": len(spans)}


@router.get("/traces/sql")
async def sql_traces(
    limit: int = Query(100, le=1000),
    _: User = Depends(get_current_user),
):
    return {"traces": get_sql_traces(limit=limit), "total": 0}
