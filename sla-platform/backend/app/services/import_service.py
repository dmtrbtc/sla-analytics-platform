import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.enums import ImportStatus
from app.domain.models import ImportSession
from app.tasks.import_tasks import run_import_pipeline


def _compute_sha256(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _extract_period_from_filename(filename: str) -> Optional[datetime]:
    parts = filename.split("_")
    for p in parts:
        try:
            if len(p) == 10 and p[4] == "-" and p[7] == "-":
                return datetime.strptime(p, "%Y-%m-%d")
        except ValueError:
            continue
    return None


def _ensure_import_dir(import_id: UUID) -> Path:
    path = Path(settings.DATA_DIR) / "imports" / str(import_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


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
        file_content: bytes,
        filename: str,
        file_type: str,
    ) -> ImportSession:
        imp = await db.get(ImportSession, session_id)
        if not imp:
            raise ValueError(f"ImportSession {session_id} not found")

        import_dir = _ensure_import_dir(session_id)
        dest = import_dir / filename
        dest.write_bytes(file_content)

        sha256 = _compute_sha256(str(dest))
        row_count = _count_csv_rows(str(dest))

        if file_type == "backlog":
            imp.backlog_file = filename
            imp.backlog_sha256 = sha256
            imp.backlog_rows = row_count
            period = _extract_period_from_filename(filename)
            if period:
                imp.period_start = period
        elif file_type == "history":
            imp.history_file = filename
            imp.history_sha256 = sha256
            imp.history_rows = row_count
            period = _extract_period_from_filename(filename)
            if period:
                imp.period_end = period

        if imp.backlog_file and imp.history_file:
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

        if imp.status not in (ImportStatus.VALIDATING.value, ImportStatus.FAILED.value):
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
    async def list_sessions(db: AsyncSession) -> list[ImportSession]:
        result = await db.execute(
            select(ImportSession).order_by(ImportSession.created_at.desc())
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


def _count_csv_rows(file_path: str) -> int:
    import csv

    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        row_count = sum(1 for _ in reader)
    return max(0, row_count - 1)
