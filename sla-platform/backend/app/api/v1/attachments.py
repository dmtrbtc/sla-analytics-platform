"""Enterprise File Attachments — upload, download, delete, audit, storage abstraction."""
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import sync_session_factory
from app.core.dependencies import get_current_user, require_admin
from app.domain.models import User

router = APIRouter(dependencies=[Depends(get_current_user)])

STORAGE_DIR = os.path.join(settings.DATA_DIR, "attachments")
os.makedirs(STORAGE_DIR, exist_ok=True)

ALLOWED_MIMES = {
    "text/csv": ".csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "application/zip": ".zip",
    "application/vnd.ms-excel": ".xls",
    "application/json": ".json",
    "text/markdown": ".md",
}
MAX_FILE_SIZE = 100 * 1024 * 1024


@router.post("/upload")
async def upload_attachment(
    file: UploadFile = File(...),
    ticket_id: int = Form(None),
    import_id: str = Form(None),
    description: str = Form(""),
    current_user: User = Depends(get_current_user),
):
    """Upload a file attachment."""
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(400, f"File size exceeds {MAX_FILE_SIZE // 1024 // 1024}MB limit")

    ext = os.path.splitext(file.filename or "")[1].lower() or ".bin"
    if file.content_type and file.content_type not in ALLOWED_MIMES:
        raise HTTPException(400, f"File type '{file.content_type}' not allowed")

    attachment_id = str(uuid.uuid4())
    stored_name = f"{attachment_id}{ext}"
    filepath = os.path.join(STORAGE_DIR, stored_name)

    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    with open(filepath, "wb") as f:
        f.write(content)

    size_bytes = len(content)
    db = sync_session_factory()
    try:
        db.execute(
            text("""
                INSERT INTO attachments (id, filename, stored_name, mime_type, size_bytes, file_hash, ticket_id, import_id, description, uploaded_by, created_at)
                VALUES (:id, :filename, :stored, :mime, :size, :hash, :tid, :iid, :desc, :uid, NOW())
            """),
            {
                "id": attachment_id, "filename": file.filename, "stored": stored_name,
                "mime": file.content_type or "application/octet-stream", "size": size_bytes,
                "hash": file_hash, "tid": ticket_id, "iid": import_id, "desc": description,
                "uid": str(current_user.id),
            },
        )
        db.commit()
        return {
            "id": attachment_id,
            "filename": file.filename,
            "size_bytes": size_bytes,
            "mime_type": file.content_type,
            "ticket_id": ticket_id,
            "import_id": import_id,
            "description": description,
        }
    finally:
        db.close()


@router.get("/{attachment_id}")
async def get_attachment(attachment_id: str, _: User = Depends(get_current_user)):
    """Get attachment metadata and serve file."""
    db = sync_session_factory()
    try:
        row = db.execute(
            text("SELECT id, filename, stored_name, mime_type, size_bytes, file_hash, ticket_id, import_id, description, uploaded_by, created_at FROM attachments WHERE id = :id"),
            {"id": attachment_id},
        ).first()
        if not row:
            raise HTTPException(404, "Attachment not found")

        filepath = os.path.join(STORAGE_DIR, row.stored_name)
        if not os.path.exists(filepath):
            raise HTTPException(404, "File not found on storage")

        return FileResponse(
            filepath,
            media_type=row.mime_type or "application/octet-stream",
            filename=row.filename,
            headers={
                "X-Attachment-Id": row.id,
                "X-File-Hash": row.file_hash or "",
                "X-Size-Bytes": str(row.size_bytes),
            },
        )
    finally:
        db.close()


@router.get("")
async def list_attachments(
    ticket_id: int = Query(None),
    import_id: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: User = Depends(get_current_user),
):
    """List attachments with optional filters."""
    db = sync_session_factory()
    try:
        q = "SELECT id, filename, stored_name, mime_type, size_bytes, ticket_id, import_id, description, uploaded_by, created_at FROM attachments WHERE 1=1"
        count_q = "SELECT COUNT(*) FROM attachments WHERE 1=1"
        params: dict[str, Any] = {}
        if ticket_id:
            q += " AND ticket_id = :tid"; count_q += " AND ticket_id = :tid"; params["tid"] = ticket_id
        if import_id:
            q += " AND import_id = :iid"; count_q += " AND import_id = :iid"; params["iid"] = import_id
        q += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        params["limit"] = limit; params["offset"] = offset

        rows = db.execute(text(q), params).mappings().all()
        total = db.execute(text(count_q), params).scalar() or 0
        return {"attachments": [dict(r) for r in rows], "total": total}
    finally:
        db.close()


@router.delete("/{attachment_id}")
async def delete_attachment(attachment_id: str, _: User = Depends(require_admin)):
    """Delete an attachment (file + metadata)."""
    db = sync_session_factory()
    try:
        row = db.execute(text("SELECT stored_name FROM attachments WHERE id = :id"), {"id": attachment_id}).first()
        if not row:
            raise HTTPException(404, "Attachment not found")

        filepath = os.path.join(STORAGE_DIR, row.stored_name)
        if os.path.exists(filepath):
            os.remove(filepath)

        db.execute(text("DELETE FROM attachments WHERE id = :id"), {"id": attachment_id})
        db.commit()
        return {"deleted": True}
    finally:
        db.close()
