import hashlib
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, sync_session_factory
from app.domain.models import ImportSession
from app.domain.schemas import (
    ImportSessionResponse,
    ImportUploadResponse,
    PipelineStatusResponse,
    MessageResponse,
)
from app.services.audit_service import AuditService
from app.services.import_service import ImportService
from app.tasks.import_tasks import run_import_pipeline

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
):
    try:
        session = await ImportService.create_session(db)

        if backlog:
            content = await backlog.read()
            ext = _detect_file_type(backlog.filename or "")
            await ImportService.upload_file(
                db, session.id, content, backlog.filename or "backlog.csv", ext or "backlog"
            )

        if history:
            content = await history.read()
            ext = _detect_file_type(history.filename or "")
            await ImportService.upload_file(
                db, session.id, content, history.filename or "history.csv", ext or "history"
            )

        return ImportUploadResponse(
            id=session.id,
            status=session.status,
            message="Session created. Call /sessions/{id}/start to begin processing.",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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
):
    try:
        session = await ImportService.start_processing(db, session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
):
    session = await ImportService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Import session not found")

    from app.tasks.import_tasks import run_import_pipeline

    session.status = "parsing"
    session.error_details = []
    session.stats = {}
    db.add(session)
    await db.commit()

    _sync_audit("import_reprocessed", "import_session", str(session.id), details={"status": "restarted"})
    run_import_pipeline.delay(str(session_id))

    return PipelineStatusResponse(
        import_id=session.id,
        status=session.status,
        stats={},
        error_count=0,
    )


def _sync_audit(action: str, resource_type: str, resource_id: str, details: Optional[dict] = None) -> None:
    try:
        sync_db = sync_session_factory()
        AuditService.log(sync_db, action=action, resource_type=resource_type, resource_id=resource_id, details=details)
        sync_db.close()
    except Exception:
        pass


def _detect_file_type(filename: str) -> Optional[str]:
    low = filename.lower()
    if "backlog" in low:
        return "backlog"
    if "history" in low:
        return "history"
    return None
