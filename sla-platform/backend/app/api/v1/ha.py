"""HA + Resilience endpoints — health checks, failover status, autoscaling metrics."""
from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user, require_admin
from app.domain.models import User
from app.services.ha.resilience import (
    check_redis_health, check_postgres_replicas, check_queue_failover,
    graceful_degradation_check, get_worker_autoscaling_metrics,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/redis")
async def ha_redis_status(_: User = Depends(require_admin)):
    return check_redis_health()


@router.get("/postgres")
async def ha_postgres_status(_: User = Depends(require_admin)):
    return check_postgres_replicas()


@router.get("/queues")
async def ha_queue_status(_: User = Depends(require_admin)):
    return check_queue_failover()


@router.get("/degradation")
async def ha_degradation_status(_: User = Depends(require_admin)):
    return graceful_degradation_check()


@router.get("/autoscaling")
async def ha_autoscaling_metrics(_: User = Depends(require_admin)):
    return get_worker_autoscaling_metrics()
