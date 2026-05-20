"""Operations center — self-healing, stuck detection, recovery, diagnostics snapshots."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user, require_admin
from app.domain.models import User
from app.services.operations.self_healing import (
    detect_stuck_imports, detect_stalled_views, detect_queue_lag_anomaly,
    auto_mitigate, recovery_snapshot, run_recovery_policies,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/stuck-imports")
async def stuck_imports(hours: int = Query(2, ge=1, le=48), _: User = Depends(require_admin)):
    return {"stuck": detect_stuck_imports(hours=hours), "total": 0}


@router.get("/stalled-views")
async def stalled_views(_: User = Depends(require_admin)):
    return {"views": detect_stalled_views()}


@router.get("/queue-lag")
async def queue_lag(threshold: int = Query(100, ge=10), _: User = Depends(require_admin)):
    return detect_queue_lag_anomaly(max_acceptable=threshold)


@router.post("/auto-mitigate")
async def trigger_auto_mitigate(_: User = Depends(require_admin)):
    actions = auto_mitigate()
    return {"actions": actions, "total": len(actions)}


@router.get("/recovery-snapshot")
async def trigger_recovery_snapshot(_: User = Depends(require_admin)):
    return recovery_snapshot()


@router.get("/recovery-policies")
async def recovery_policies(_: User = Depends(require_admin)):
    return {"policies": run_recovery_policies()}
