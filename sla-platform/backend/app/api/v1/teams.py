from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.database import get_sync_db
from app.core.dependencies import get_current_user, require_admin
from app.domain.models import Team, User
from app.domain.schemas import TeamCreate, TeamResponse, TeamUpdate
from app.services.team_service import TeamService

router = APIRouter()


def _team_to_dict(t: Team) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "queue_prefix": t.queue_prefix,
        "description": t.description,
        "is_active": t.is_active,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "lead_user_id": str(t.lead_user_id) if getattr(t, "lead_user_id", None) else None,
        "color": getattr(t, "color", None),
        "response_target_seconds": getattr(t, "response_target_seconds", None),
        "resolution_target_seconds": getattr(t, "resolution_target_seconds", None),
        "escalation_chain": getattr(t, "escalation_chain", None) or [],
        "queues": getattr(t, "queues", None) or [],
    }


@router.get("", response_model=dict)
async def list_teams(
    active_only: bool = Query(False),
    db=Depends(get_sync_db),
):
    teams = TeamService.list_teams(db, active_only=active_only)
    return {"teams": [_team_to_dict(t) for t in teams]}


@router.post("", response_model=dict, status_code=201)
async def create_team(
    payload: TeamCreate,
    db=Depends(get_sync_db),
    _: User = Depends(require_admin),
):
    extra = payload.model_dump(exclude_unset=True,
                               exclude={"name", "queue_prefix", "description"})
    team = TeamService.create_team(
        db,
        name=payload.name,
        queue_prefix=payload.queue_prefix or payload.name[:3].lower(),
        description=payload.description,
        **extra,
    )
    return _team_to_dict(team)


@router.get("/{team_id}", response_model=dict)
async def get_team(
    team_id: int,
    db=Depends(get_sync_db),
):
    team = TeamService.get_team(db, team_id)
    if not team:
        raise HTTPException(404, detail="Team not found")
    return _team_to_dict(team)


# Frontends commonly send PATCH for partial updates; accept both verbs so
# we don't ship another 405 surprise.
@router.api_route("/{team_id}", methods=["PUT", "PATCH"], response_model=dict)
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
    return _team_to_dict(team)


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


# ----- Team membership (v1.4) ---------------------------------------------


class _MemberAdd(BaseModel):
    user_id: UUID


@router.get("/{team_id}/members", response_model=dict)
async def list_team_members(
    team_id: int,
    db=Depends(get_sync_db),
    _: User = Depends(get_current_user),
):
    if not TeamService.get_team(db, team_id):
        raise HTTPException(404, "Team not found")
    return {"members": TeamService.list_members(db, team_id)}


@router.post("/{team_id}/members", response_model=dict, status_code=201)
async def add_team_member(
    team_id: int,
    payload: _MemberAdd,
    db=Depends(get_sync_db),
    _: User = Depends(require_admin),
):
    if not TeamService.get_team(db, team_id):
        raise HTTPException(404, "Team not found")
    TeamService.add_member(db, team_id, payload.user_id)
    return {"team_id": team_id, "user_id": str(payload.user_id), "added": True}


@router.delete("/{team_id}/members/{user_id}", response_model=dict)
async def remove_team_member(
    team_id: int,
    user_id: UUID,
    db=Depends(get_sync_db),
    _: User = Depends(require_admin),
):
    if not TeamService.remove_member(db, team_id, user_id):
        raise HTTPException(404, "Member not in team")
    return {"team_id": team_id, "user_id": str(user_id), "removed": True}


# ----- Admin cleanup ------------------------------------------------------


@router.post("/cleanup-dummies", response_model=dict)
async def cleanup_dummies(
    db=Depends(get_sync_db),
    _: User = Depends(require_admin),
):
    """Remove leftover fixture teams (name='Incomplete' / 'Support Team')."""
    deleted = TeamService.cleanup_dummies(db)
    return {"deleted": deleted}
