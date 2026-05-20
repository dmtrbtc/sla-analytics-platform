"""Enterprise File Storage — local abstraction, S3-ready interface, retention, quotas."""
from __future__ import annotations

import os
import shutil
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import BinaryIO, Optional
from uuid import UUID

from app.core.config import settings

logger = logging.getLogger(__name__)

STORAGE_BACKEND = getattr(settings, "STORAGE_BACKEND", "local")
STORAGE_DIR = os.path.join(settings.DATA_DIR, "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)


class StorageBackend:
    """Abstract storage backend — local implementation, S3-ready interface."""

    def store(self, path: str, content: bytes) -> str:
        raise NotImplementedError

    def retrieve(self, path: str) -> Optional[bytes]:
        raise NotImplementedError

    def delete(self, path: str) -> bool:
        raise NotImplementedError

    def exists(self, path: str) -> bool:
        raise NotImplementedError

    def size(self, path: str) -> int:
        raise NotImplementedError

    def cleanup(self, retention_days: int = 90) -> int:
        """Delete files older than retention_days. Returns count deleted."""
        raise NotImplementedError


class LocalStorage(StorageBackend):
    """Local filesystem storage."""

    def _resolve(self, path: str) -> str:
        safe = os.path.basename(path)
        return os.path.join(STORAGE_DIR, safe)

    def store(self, path: str, content: bytes) -> str:
        fp = self._resolve(path)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "wb") as f:
            f.write(content)
        return fp

    def retrieve(self, path: str) -> Optional[bytes]:
        fp = self._resolve(path)
        if not os.path.exists(fp):
            return None
        with open(fp, "rb") as f:
            return f.read()

    def delete(self, path: str) -> bool:
        fp = self._resolve(path)
        if os.path.exists(fp):
            os.remove(fp)
            return True
        return False

    def exists(self, path: str) -> bool:
        return os.path.exists(self._resolve(path))

    def size(self, path: str) -> int:
        fp = self._resolve(path)
        return os.path.getsize(fp) if os.path.exists(fp) else 0

    def cleanup(self, retention_days: int = 90) -> int:
        count = 0
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        for fname in os.listdir(STORAGE_DIR):
            fp = os.path.join(STORAGE_DIR, fname)
            if os.path.isfile(fp):
                mtime = datetime.fromtimestamp(os.path.getmtime(fp), tz=timezone.utc)
                if mtime < cutoff:
                    os.remove(fp)
                    count += 1
        logger.info("Storage cleanup: removed %d files older than %d days", count, retention_days)
        return count


def get_storage() -> StorageBackend:
    """Factory — returns configured storage backend."""
    return LocalStorage()


def compute_file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate_file_size(size_bytes: int, max_mb: int = 100) -> bool:
    return size_bytes <= max_mb * 1024 * 1024


def validate_mime_type(mime: str) -> bool:
    allowed = {
        "text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/pdf", "text/plain", "application/zip", "application/vnd.ms-excel",
        "application/json", "text/markdown", "image/png", "image/jpeg",
    }
    return mime in allowed
