from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.database import get_sync_db
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("/log")
async def list_audit_log(
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    db=Depends(get_sync_db),
):
    entries, total = AuditService.list_logs(
        db, limit=limit, offset=offset, action=action, resource_type=resource_type,
    )
    return {
        "entries": [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "actor_id": str(e.actor_id) if e.actor_id else None,
                "action": e.action,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "details": e.details,
                "ip_address": str(e.ip_address) if e.ip_address else None,
            }
            for e in entries
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
