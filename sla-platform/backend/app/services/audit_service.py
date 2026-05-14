"""Audit log service for tracking user actions."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from app.core.database import sync_session_factory
from app.domain.models import AuditLog


class AuditService:

    @staticmethod
    def log(
        db: Session,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        actor_id: Optional[UUID] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        entry = AuditLog(
            timestamp=datetime.now(timezone.utc),
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
        )
        db.add(entry)
        db.commit()
        return entry

    @staticmethod
    def log_sync(
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        actor_id: Optional[UUID] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        try:
            db = sync_session_factory()
            AuditService.log(
                db,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                actor_id=actor_id,
                details=details,
                ip_address=ip_address,
            )
            db.close()
        except Exception:
            pass

    @staticmethod
    def list_logs(
        db: Session,
        limit: int = 100,
        offset: int = 0,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
    ) -> tuple[list[AuditLog], int]:
        q = select(AuditLog)
        count_q = select(func.count(AuditLog.id))
        if action:
            q = q.where(AuditLog.action == action)
            count_q = count_q.where(AuditLog.action == action)
        if resource_type:
            q = q.where(AuditLog.resource_type == resource_type)
            count_q = count_q.where(AuditLog.resource_type == resource_type)

        total = db.execute(count_q).scalar() or 0
        q = q.order_by(desc(AuditLog.timestamp)).offset(offset).limit(limit)
        rows = db.execute(q).scalars().all()
        return list(rows), total
