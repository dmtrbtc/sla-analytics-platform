import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import ImportStatus
from app.domain.models import ImportSession
from app.tasks.import_tasks import run_import_pipeline


def sanitize_filename(filename: str) -> str:
    filename = os.path.basename(filename)
    filename = filename.replace("/", "_").replace("\\", "_")
    return filename


def _extract_period_from_filename(filename: str) -> Optional[datetime]:
    parts = filename.split("_")
    for p in parts:
        try:
            if len(p) == 10 and p[4] == "-" and p[7] == "-":
                return datetime.strptime(p, "%Y-%m-%d")
        except ValueError:
            continue
    return None


class ImportService:

    @staticmethod
    async def create_session(db: AsyncSession) -> ImportSession:
        session = ImportSession(
            id=uuid.uuid4(),
            status=ImportStatus.DRAFT.value,
            stats={},
            error_details=[],
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def upload_file(
        db: AsyncSession,
        session_id: UUID,
        filename: str,
        file_type: str,
        sha256: str,
        row_count: int,
    ) -> ImportSession:
        imp = await db.get(ImportSession, session_id)
        if not imp:
            raise ValueError(f"ImportSession {session_id} not found")

        safe_name = sanitize_filename(filename)

        if file_type == "backlog":
            imp.backlog_file = safe_name
            imp.backlog_sha256 = sha256
            imp.backlog_rows = row_count
            period = _extract_period_from_filename(safe_name)
            if period:
                imp.period_start = period
        elif file_type == "history":
            imp.history_file = safe_name
            imp.history_sha256 = sha256
            imp.history_rows = row_count
            period = _extract_period_from_filename(safe_name)
            if period:
                imp.period_end = period

        if imp.status == ImportStatus.DRAFT.value:
            imp.status = ImportStatus.VALIDATING.value

        db.add(imp)
        await db.commit()
        await db.refresh(imp)
        return imp

    @staticmethod
    async def start_processing(
        db: AsyncSession, session_id: UUID
    ) -> ImportSession:
        imp = await db.get(ImportSession, session_id)
        if not imp:
            raise ValueError(f"ImportSession {session_id} not found")

        if imp.status not in (ImportStatus.DRAFT.value, ImportStatus.VALIDATING.value, ImportStatus.FAILED.value):
            raise ValueError(
                f"Cannot start processing from status '{imp.status}'"
            )

        imp.status = ImportStatus.PARSING.value
        db.add(imp)
        await db.commit()
        await db.refresh(imp)

        run_import_pipeline.delay(str(session_id))

        return imp

    @staticmethod
    async def get_session(
        db: AsyncSession, session_id: UUID
    ) -> Optional[ImportSession]:
        return await db.get(ImportSession, session_id)

    @staticmethod
    async def list_sessions(
        db: AsyncSession,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ImportSession]:
        result = await db.execute(
            select(ImportSession)
            .order_by(ImportSession.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_status(
        db: AsyncSession, session_id: UUID, status: str
    ) -> None:
        imp = await db.get(ImportSession, session_id)
        if imp:
            imp.status = status
            if status == ImportStatus.COMPLETED.value:
                imp.completed_at = datetime.now(timezone.utc)
            db.add(imp)
            await db.commit()

    @staticmethod
    async def add_error(
        db: AsyncSession,
        session_id: UUID,
        error: str,
        step: Optional[str] = None,
    ) -> None:
        imp = await db.get(ImportSession, session_id)
        if imp:
            err_list = list(imp.error_details or [])
            err_list.append(
                {"step": step or "unknown", "message": error, "timestamp": datetime.now(timezone.utc).isoformat()}
            )
            imp.error_details = err_list
            db.add(imp)
            await db.commit()

    @staticmethod
    async def update_stats(
        db: AsyncSession,
        session_id: UUID,
        stats: dict,
    ) -> None:
        imp = await db.get(ImportSession, session_id)
        if imp:
            current = dict(imp.stats or {})
            current.update(stats)
            imp.stats = current
            db.add(imp)
            await db.commit()

