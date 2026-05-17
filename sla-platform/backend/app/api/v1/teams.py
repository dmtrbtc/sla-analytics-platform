from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.database import get_sync_db
from app.core.dependencies import require_admin
from app.domain.models import Team, User
from app.domain.schemas import TeamCreate, TeamResponse, TeamUpdate
from app.services.team_service import TeamService

router = APIRouter()


@router.get("", response_model=dict)
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


@router.post("", response_model=TeamResponse, status_code=201)
async def create_team(
    payload: TeamCreate,
    db=Depends(get_sync_db),
    _: User = Depends(require_admin),
):
    team = TeamService.create_team(
        db,
        name=payload.name,
        queue_prefix=payload.queue_prefix or payload.name[:3].lower(),
        description=payload.description,
    )
    return team


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: int,
    db=Depends(get_sync_db),
):
    team = TeamService.get_team(db, team_id)
    if not team:
        raise HTTPException(404, detail="Team not found")
    return team


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int,
    payload: TeamUpdate,
    db=Depends(get_sync_db),
    _: User = Depends(require_admin),
):
    update_data = payload.model_dump(exclude_unset=True)
    team = TeamService.update_team(db, team_id, **update_data)
    if not team:
        raise HTTPException(404, detail="Team not found")
    return team


@router.delete("/{team_id}", response_model=dict)
async def delete_team(
    team_id: int,
    db=Depends(get_sync_db),
    _: User = Depends(require_admin),
):
    ok = TeamService.delete_team(db, team_id)
    if not ok:
        raise HTTPException(404, detail="Team not found")
    return {"status": "deleted"}
