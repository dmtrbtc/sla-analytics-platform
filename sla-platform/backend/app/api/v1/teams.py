from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.database import get_sync_db
from app.core.dependencies import require_admin
from app.domain.models import Team, User
from app.services.team_service import TeamService

router = APIRouter()


@router.get("")
async def list_teams(
    active_only: bool = Query(False),
    db=Depends(get_sync_db),
):
    teams = TeamService.list_teams(db, active_only=active_only)
    return {
        "teams": [
            {
                "id": t.id,
                "name": t.name,
                "queue_prefix": t.queue_prefix,
                "description": t.description,
                "is_active": t.is_active,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in teams
        ]
    }


@router.post("")
async def create_team(
    payload: dict,
    db=Depends(get_sync_db),
    _: User = Depends(require_admin),
):
    name = payload.get("name")
    queue_prefix = payload.get("queue_prefix")
    if not name or not queue_prefix:
        raise HTTPException(400, detail="name and queue_prefix are required")
    team = TeamService.create_team(
        db,
        name=name,
        queue_prefix=queue_prefix,
        description=payload.get("description"),
    )
    return {
        "id": team.id,
        "name": team.name,
        "queue_prefix": team.queue_prefix,
        "description": team.description,
        "is_active": team.is_active,
    }


@router.get("/{team_id}")
async def get_team(
    team_id: int,
    db=Depends(get_sync_db),
):
    team = TeamService.get_team(db, team_id)
    if not team:
        raise HTTPException(404, detail="Team not found")
    return {
        "id": team.id,
        "name": team.name,
        "queue_prefix": team.queue_prefix,
        "description": team.description,
        "is_active": team.is_active,
        "created_at": team.created_at.isoformat() if team.created_at else None,
    }


@router.put("/{team_id}")
async def update_team(
    team_id: int,
    payload: dict,
    db=Depends(get_sync_db),
    _: User = Depends(require_admin),
):
    team = TeamService.update_team(db, team_id, **payload)
    if not team:
        raise HTTPException(404, detail="Team not found")
    return {
        "id": team.id,
        "name": team.name,
        "queue_prefix": team.queue_prefix,
        "description": team.description,
        "is_active": team.is_active,
    }


@router.delete("/{team_id}")
async def delete_team(
    team_id: int,
    db=Depends(get_sync_db),
    _: User = Depends(require_admin),
):
    ok = TeamService.delete_team(db, team_id)
    if not ok:
        raise HTTPException(404, detail="Team not found")
    return {"status": "deleted"}
