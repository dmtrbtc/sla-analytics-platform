import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import sync_session_factory
from app.core.dependencies import require_admin
from app.domain.models import User
from app.services.audit_service import AuditService
from app.tasks.report_tasks import EXPORT_DIR, _REPORT_STATUSES, generate_report, get_report_status

logger = logging.getLogger(__name__)

router = APIRouter()


def _sync_audit(action: str, resource_type: str, resource_id: str, details: Optional[dict] = None) -> None:
    try:
        sync_db = sync_session_factory()
        AuditService.log(sync_db, action=action, resource_type=resource_type, resource_id=resource_id, details=details)
        sync_db.close()
    except Exception:
        logger.warning("Audit log failed for %s %s %s", action, resource_type, resource_id, exc_info=True)


@router.post("/generate", response_model=dict)
async def generate(
    report_type: str = Query(..., description="sla_breaches|team_performance|ticket_lifecycle|imports_summary"),
    fmt: str = Query("xlsx", description="xlsx|csv"),
    import_id: Optional[str] = Query(None),
    team_prefix: Optional[str] = Query(None),
    _: User = Depends(require_admin),
):
    params = {}
    if import_id:
        params["import_id"] = import_id
    if team_prefix:
        params["team_prefix"] = team_prefix

    task = generate_report.delay(report_type, fmt, params)
    _sync_audit("report_generated", "report", task.id, details={"report_type": report_type, "format": fmt})
    return {
        "status": "started",
        "task_id": task.id,
        "report_type": report_type,
        "format": fmt,
        "message": "Report generation started. Poll /reports/status/{task_id} for completion.",
    }


@router.get("/status/{task_id}", response_model=dict)
async def report_status(task_id: str):
    status = get_report_status(task_id)
    if not status:
        from celery.result import AsyncResult
        from app.core.celery_app import celery_app

        result = AsyncResult(task_id, app=celery_app)
        if result.failed():
            return {"task_id": task_id, "status": "failed", "error": str(result.info)}
        if result.successful():
            return {"task_id": task_id, "status": "completed", "result": result.result}
        return {"task_id": task_id, "status": result.state.lower()}
    return {"task_id": task_id, **status}


@router.get("", response_model=dict)
async def list_reports():
    reports = []
    os.makedirs(EXPORT_DIR, exist_ok=True)
    for fname in sorted(os.listdir(EXPORT_DIR), reverse=True)[:100]:
        fpath = os.path.join(EXPORT_DIR, fname)
        if os.path.isfile(fpath):
            reports.append({
                "filename": fname,
                "size_bytes": os.path.getsize(fpath),
                "modified": os.path.getmtime(fpath),
            })
    return {"reports": reports}


@router.get("/{report_id}", response_model=dict)
async def get_report(report_id: str):
    status = get_report_status(report_id)
    if not status:
        raise HTTPException(404, detail="Report not found")
    return {"report_id": report_id, **status}


@router.get("/{filename}/download")
async def download_report(filename: str):
    safe_path = os.path.normpath(os.path.join(EXPORT_DIR, filename))
    if not safe_path.startswith(os.path.normpath(EXPORT_DIR) + os.sep):
        raise HTTPException(400, detail="Invalid filename")
    if not os.path.exists(safe_path):
        raise HTTPException(404, detail="Report file not found")

    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if filename.endswith(".csv"):
        media_type = "text/csv"

    return FileResponse(
        path=safe_path,
        media_type=media_type,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
