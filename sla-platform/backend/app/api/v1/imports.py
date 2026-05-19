import hashlib
import logging
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db, sync_session_factory
from app.core.dependencies import require_admin
from app.domain.enums import ImportStatus
from app.domain.models import ImportSession, User
from app.domain.schemas import (
    ImportSessionResponse,
    ImportUploadResponse,
    PipelineStatusResponse,
)
from app.services.audit_service import AuditService
from app.services.import_service import ImportService, sanitize_filename

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/sessions", response_model=list[ImportSessionResponse])
async def list_sessions(db: AsyncSession = Depends(get_db)):
    sessions = await ImportService.list_sessions(db)
    return [
        ImportSessionResponse(
            id=s.id,
            status=s.status,
            backlog_file=s.backlog_file,
            history_file=s.history_file,
            backlog_sha256=s.backlog_sha256,
            history_sha256=s.history_sha256,
            backlog_rows=s.backlog_rows,
            history_rows=s.history_rows,
            period_start=s.period_start,
            period_end=s.period_end,
            stats=s.stats or {},
            error_details=s.error_details or [],
            imported_by=s.imported_by,
            created_at=s.created_at,
            updated_at=s.updated_at,
            completed_at=s.completed_at,
        )
        for s in sessions
    ]


@router.post("/sessions", response_model=ImportUploadResponse)
async def create_session(
    backlog: Optional[UploadFile] = File(None),
    history: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    try:
        session = await ImportService.create_session(db)

        if backlog:
            sha256, row_count = await _stream_upload_to_disk(
                backlog, session.id, "backlog"
            )
            await ImportService.upload_file(
                db, session.id, backlog.filename or "backlog.csv", "backlog",
                sha256, row_count,
            )

        if history:
            sha256, row_count = await _stream_upload_to_disk(
                history, session.id, "history"
            )
            await ImportService.upload_file(
                db, session.id, history.filename or "history.csv", "history",
                sha256, row_count,
            )

        return ImportUploadResponse(
            id=session.id,
            status=session.status,
            message="Session created. Call /sessions/{id}/start to begin processing.",
        )
    except Exception as e:
        logger.warning("Upload failed: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail="Upload failed")


@router.get("/sessions/{session_id}", response_model=ImportSessionResponse)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    session = await ImportService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Import session not found")
    return ImportSessionResponse(
        id=session.id,
        status=session.status,
        backlog_file=session.backlog_file,
        history_file=session.history_file,
        backlog_sha256=session.backlog_sha256,
        history_sha256=session.history_sha256,
        backlog_rows=session.backlog_rows,
        history_rows=session.history_rows,
        period_start=session.period_start,
        period_end=session.period_end,
        stats=session.stats or {},
        error_details=session.error_details or [],
        imported_by=session.imported_by,
        created_at=session.created_at,
        updated_at=session.updated_at,
        completed_at=session.completed_at,
    )


@router.post("/sessions/{session_id}/start", response_model=PipelineStatusResponse)
async def start_processing(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    try:
        session = await ImportService.start_processing(db, session_id)
    except ValueError as e:
        logger.warning("Invalid session state: %s", e)
        raise HTTPException(status_code=400, detail="Invalid session state")
    return PipelineStatusResponse(
        import_id=session.id,
        status=session.status,
        stats=session.stats or {},
        error_count=len(session.error_details or []),
    )


@router.post("/sessions/{session_id}/reprocess", response_model=PipelineStatusResponse)
async def reprocess_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    session = await ImportService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Import session not found")

    session.status = ImportStatus.FAILED.value
    session.error_details = []
    session.stats = {}
    db.add(session)
    await db.commit()

    background_tasks.add_task(_sync_audit, "import_reprocessed", "import_session", str(session.id), {"status": "restarted"})
    try:
        await ImportService.start_processing(db, session_id)
    except ValueError as e:
        logger.warning("Reprocess failed: %s", e)
        raise HTTPException(status_code=400, detail=str(e))

    return PipelineStatusResponse(
        import_id=session.id,
        status=session.status,
        stats={},
        error_count=0,
    )


@router.get("/sessions/{session_id}/progress")
async def get_import_progress(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    session = await ImportService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Import session not found")
    stats = dict(session.stats or {})
    active = session.status in ("validating", "parsing", "normalizing", "rebuilding", "computing_sla")
    stage_order = ["validate", "backlog", "parse", "normalize", "rebuild", "compute_sla", "complete"]
    stage_map = {"validating": "validate", "parsing": "parse", "normalizing": "normalize", "rebuilding": "rebuild", "computing_sla": "compute_sla"}
    current_stage = stage_map.get(session.status, session.status)
    stage_idx = stage_order.index(current_stage) if current_stage in stage_order else 0
    progress_pct = round((stage_idx / max(len(stage_order) - 1, 1)) * 100) if not session.completed_at else 100

    return {
        "session_id": session_id,
        "status": session.status,
        "progress_pct": min(progress_pct, 100),
        "current_stage": current_stage,
        "active": active,
        "rows_processed": stats.get("events_parsed") or stats.get("normalized") or 0,
        "rows_total": session.history_rows or 0,
        "tickets_processed": stats.get("tickets") or stats.get("snapshots") or 0,
        "rows_per_second": stats.get("rows_per_second"),
        "eta_seconds": stats.get("eta_seconds"),
        "elapsed_seconds": stats.get("elapsed_seconds"),
        "memory_mb": stats.get("memory_mb"),
        "errors": len(session.error_details or []),
    }


def _sync_audit(action: str, resource_type: str, resource_id: str, details: Optional[dict] = None) -> None:
    try:
        sync_db = sync_session_factory()
        AuditService.log(sync_db, action=action, resource_type=resource_type, resource_id=resource_id, details=details)
        sync_db.close()
    except Exception:
        logger.warning("Audit log failed for %s %s %s", action, resource_type, resource_id, exc_info=True)


def _detect_file_type(filename: str) -> Optional[str]:
    low = filename.lower()
    if "backlog" in low:
        return "backlog"
    if "history" in low:
        return "history"
    return None


async def _stream_upload_to_disk(
    upload: UploadFile, session_id: UUID, file_type: str
) -> tuple[str, int]:
    filename = upload.filename or f"{file_type}.csv"
    from app.utils.file_validator import validate_extension, validate_mime
    if not validate_extension(filename):
        raise HTTPException(status_code=400, detail=f"File extension not allowed: {filename}")
    if upload.content_type and not validate_mime(upload.content_type):
        raise HTTPException(status_code=400, detail=f"Content-Type not allowed: {upload.content_type}")

    total_size = 0
    import_dir = Path(settings.DATA_DIR) / "imports" / str(session_id)
    import_dir.mkdir(parents=True, exist_ok=True)
    safe_name = sanitize_filename(filename)
    dest = import_dir / safe_name

    h = hashlib.sha256()
    row_count = 0
    header_skipped = False
    with open(dest, "wb") as f:
        async for chunk in upload.iter_chunks():
            data = chunk[0] if isinstance(chunk, tuple) else chunk
            if not data:
                break
            total_size += len(data)
            if total_size > 100 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="File exceeds maximum size of 100MB")
            f.write(data)
            h.update(data)
            if not header_skipped:
                header_skipped = True
            else:
                row_count += data.count(b"\n")
    return h.hexdigest(), row_count
