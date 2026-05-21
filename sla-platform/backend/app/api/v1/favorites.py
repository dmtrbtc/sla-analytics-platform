"""Favorite Queues / Queue Groups / Dashboard Presets API.

Per-user operational personalization. All endpoints scope by current_user;
admin/shared groups + presets are visible to everyone.

Endpoints:
  GET    /favorites/queues                   list user's starred queues
  POST   /favorites/queues                   star a queue                {queue_name}
  DELETE /favorites/queues/{queue_name}      unstar
  PUT    /favorites/queues/reorder           reorder                     {ordering:[names]}

  GET    /favorites/groups                   list groups (own + shared)
  POST   /favorites/groups                   create group                {name,description,color,queues,is_shared}
  GET    /favorites/groups/{id}              get group
  PATCH  /favorites/groups/{id}              update meta
  DELETE /favorites/groups/{id}              delete group
  POST   /favorites/groups/{id}/queues       add queue                   {queue_name,position}
  DELETE /favorites/groups/{id}/queues/{queue_name}   remove queue

  GET    /favorites/presets                  list dashboard presets
  POST   /favorites/presets                  create
  PATCH  /favorites/presets/{id}             update
  DELETE /favorites/presets/{id}             delete
  POST   /favorites/presets/{id}/default     mark as default for current user
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.domain.models import (
    DashboardPreset,
    FavoriteQueue,
    QueueGroup,
    QueueGroupItem,
    User,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ----- Schemas --------------------------------------------------------------


class _Star(BaseModel):
    queue_name: str = Field(min_length=1, max_length=200)


class _Reorder(BaseModel):
    ordering: list[str]


class _GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    color: Optional[str] = Field(default=None, max_length=20)
    queues: list[str] = Field(default_factory=list)
    is_shared: bool = False


class _GroupUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = None
    color: Optional[str] = Field(default=None, max_length=20)
    is_shared: Optional[bool] = None
    queues: Optional[list[str]] = None  # full replace if provided


class _GroupQueueAdd(BaseModel):
    queue_name: str = Field(min_length=1, max_length=200)
    position: int = 0


class _PresetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    workspace_kind: str = Field(default="custom", max_length=50)
    queue_group_id: Optional[UUID] = None
    layout: dict = Field(default_factory=dict)
    is_default: bool = False
    is_shared: bool = False


class _PresetUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    workspace_kind: Optional[str] = Field(default=None, max_length=50)
    queue_group_id: Optional[UUID] = None
    layout: Optional[dict] = None
    is_default: Optional[bool] = None
    is_shared: Optional[bool] = None


def _fav_to_dict(f: FavoriteQueue) -> dict:
    return {
        "queue_name": f.queue_name,
        "position": f.position,
        "starred_at": f.starred_at.isoformat() if f.starred_at else None,
    }


def _group_to_dict(g: QueueGroup, queues: list[str]) -> dict:
    return {
        "id": str(g.id),
        "user_id": str(g.user_id) if g.user_id else None,
        "name": g.name,
        "description": g.description,
        "color": g.color,
        "is_shared": g.is_shared,
        "queues": queues,
        "queue_count": len(queues),
        "created_at": g.created_at.isoformat() if g.created_at else None,
        "updated_at": g.updated_at.isoformat() if g.updated_at else None,
    }


def _preset_to_dict(p: DashboardPreset) -> dict:
    return {
        "id": str(p.id),
        "user_id": str(p.user_id) if p.user_id else None,
        "name": p.name,
        "workspace_kind": p.workspace_kind,
        "queue_group_id": str(p.queue_group_id) if p.queue_group_id else None,
        "layout": p.layout or {},
        "is_default": p.is_default,
        "is_shared": p.is_shared,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


# ----- Favorites ------------------------------------------------------------


@router.get("/queues")
async def list_favorites(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(FavoriteQueue)
        .where(FavoriteQueue.user_id == user.id)
        .order_by(FavoriteQueue.position, FavoriteQueue.starred_at)
    )).scalars().all()
    return {"queues": [_fav_to_dict(f) for f in rows], "total": len(rows)}


@router.post("/queues", status_code=201)
async def star_queue(
    payload: _Star,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Idempotent: if already starred, just return the existing row.
    existing = await db.get(FavoriteQueue, (user.id, payload.queue_name))
    if existing:
        return _fav_to_dict(existing)
    # Place at end of list.
    max_pos = (await db.execute(
        select(FavoriteQueue.position)
        .where(FavoriteQueue.user_id == user.id)
        .order_by(FavoriteQueue.position.desc())
        .limit(1)
    )).scalar()
    f = FavoriteQueue(
        user_id=user.id,
        queue_name=payload.queue_name.strip(),
        position=(max_pos or 0) + 1,
    )
    db.add(f)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # Race: already inserted
    return _fav_to_dict(f)


@router.delete("/queues/{queue_name:path}")
async def unstar_queue(
    queue_name: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    f = await db.get(FavoriteQueue, (user.id, queue_name))
    if not f:
        raise HTTPException(404, "Queue not in favorites")
    await db.delete(f)
    await db.commit()
    return {"unstarred": queue_name}


@router.put("/queues/reorder")
async def reorder_favorites(
    payload: _Reorder,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Single UPDATE per row; small lists, OK.
    for idx, qname in enumerate(payload.ordering):
        await db.execute(text("""
            UPDATE favorite_queues SET position = :p
            WHERE user_id = :u AND queue_name = :q
        """), {"p": idx, "u": str(user.id), "q": qname})
    await db.commit()
    return await list_favorites(user, db)


# ----- Queue Groups ---------------------------------------------------------


@router.get("/groups")
async def list_groups(
    include_shared: bool = Query(True),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns own groups + shared groups (unless include_shared=False)."""
    cond = QueueGroup.user_id == user.id
    if include_shared:
        cond = or_(cond, QueueGroup.is_shared == True)
    groups = (await db.execute(
        select(QueueGroup).where(cond).order_by(QueueGroup.created_at)
    )).scalars().all()

    # batch-load items
    if groups:
        ids = [g.id for g in groups]
        items = (await db.execute(
            select(QueueGroupItem)
            .where(QueueGroupItem.group_id.in_(ids))
            .order_by(QueueGroupItem.group_id, QueueGroupItem.position)
        )).scalars().all()
        by_group: dict[UUID, list[str]] = {gid: [] for gid in ids}
        for it in items:
            by_group[it.group_id].append(it.queue_name)
    else:
        by_group = {}

    return {
        "groups": [_group_to_dict(g, by_group.get(g.id, [])) for g in groups],
        "total": len(groups),
    }


@router.post("/groups", status_code=201)
async def create_group(
    payload: _GroupCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    g = QueueGroup(
        user_id=None if payload.is_shared else user.id,
        name=payload.name.strip(),
        description=payload.description,
        color=payload.color,
        is_shared=payload.is_shared,
    )
    db.add(g)
    await db.flush()
    for i, qname in enumerate(payload.queues or []):
        db.add(QueueGroupItem(group_id=g.id, queue_name=qname.strip(), position=i))
    await db.commit()
    await db.refresh(g)
    return _group_to_dict(g, list(payload.queues))


@router.get("/groups/{group_id}")
async def get_group(
    group_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    g = await db.get(QueueGroup, group_id)
    if not g or (g.user_id != user.id and not g.is_shared):
        raise HTTPException(404, "Group not found")
    items = (await db.execute(
        select(QueueGroupItem).where(QueueGroupItem.group_id == group_id)
        .order_by(QueueGroupItem.position)
    )).scalars().all()
    return _group_to_dict(g, [i.queue_name for i in items])


@router.api_route("/groups/{group_id}", methods=["PATCH", "PUT"])
async def update_group(
    group_id: UUID,
    payload: _GroupUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    g = await db.get(QueueGroup, group_id)
    if not g or (g.user_id != user.id and not g.is_shared):
        raise HTTPException(404, "Group not found")
    for field in ("name", "description", "color", "is_shared"):
        v = getattr(payload, field, None)
        if v is not None:
            setattr(g, field, v)
    if payload.queues is not None:
        # Full replace
        await db.execute(
            text("DELETE FROM queue_group_items WHERE group_id = :gid"),
            {"gid": str(group_id)},
        )
        for i, qname in enumerate(payload.queues):
            db.add(QueueGroupItem(group_id=group_id, queue_name=qname.strip(), position=i))
    await db.commit()
    await db.refresh(g)
    items = (await db.execute(
        select(QueueGroupItem).where(QueueGroupItem.group_id == group_id)
        .order_by(QueueGroupItem.position)
    )).scalars().all()
    return _group_to_dict(g, [i.queue_name for i in items])


@router.delete("/groups/{group_id}")
async def delete_group(
    group_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    g = await db.get(QueueGroup, group_id)
    if not g or (g.user_id != user.id and not g.is_shared):
        raise HTTPException(404, "Group not found")
    await db.delete(g)
    await db.commit()
    return {"deleted": str(group_id)}


@router.post("/groups/{group_id}/queues", status_code=201)
async def add_queue_to_group(
    group_id: UUID,
    payload: _GroupQueueAdd,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    g = await db.get(QueueGroup, group_id)
    if not g or (g.user_id != user.id and not g.is_shared):
        raise HTTPException(404, "Group not found")
    item = await db.get(QueueGroupItem, (group_id, payload.queue_name))
    if item:
        return {"queue_name": payload.queue_name, "position": item.position}
    db.add(QueueGroupItem(
        group_id=group_id, queue_name=payload.queue_name.strip(),
        position=payload.position,
    ))
    await db.commit()
    return {"queue_name": payload.queue_name, "position": payload.position}


@router.delete("/groups/{group_id}/queues/{queue_name:path}")
async def remove_queue_from_group(
    group_id: UUID,
    queue_name: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    g = await db.get(QueueGroup, group_id)
    if not g or (g.user_id != user.id and not g.is_shared):
        raise HTTPException(404, "Group not found")
    item = await db.get(QueueGroupItem, (group_id, queue_name))
    if not item:
        raise HTTPException(404, "Queue not in group")
    await db.delete(item)
    await db.commit()
    return {"removed": queue_name}


# ----- Dashboard Presets ----------------------------------------------------


@router.get("/presets")
async def list_presets(
    include_shared: bool = Query(True),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cond = DashboardPreset.user_id == user.id
    if include_shared:
        cond = or_(cond, DashboardPreset.is_shared == True)
    rows = (await db.execute(
        select(DashboardPreset).where(cond).order_by(DashboardPreset.created_at)
    )).scalars().all()
    return {"presets": [_preset_to_dict(p) for p in rows], "total": len(rows)}


@router.post("/presets", status_code=201)
async def create_preset(
    payload: _PresetCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p = DashboardPreset(
        user_id=None if payload.is_shared else user.id,
        name=payload.name.strip(),
        workspace_kind=payload.workspace_kind,
        queue_group_id=payload.queue_group_id,
        layout=payload.layout or {},
        is_default=payload.is_default,
        is_shared=payload.is_shared,
    )
    db.add(p)
    if payload.is_default:
        # Demote previous default for this user
        await db.execute(text("""
            UPDATE dashboard_presets SET is_default = false
            WHERE user_id = :uid AND is_default = true
        """), {"uid": str(user.id)})
    await db.commit()
    await db.refresh(p)
    return _preset_to_dict(p)


@router.api_route("/presets/{preset_id}", methods=["PATCH", "PUT"])
async def update_preset(
    preset_id: UUID,
    payload: _PresetUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p = await db.get(DashboardPreset, preset_id)
    if not p or (p.user_id != user.id and not p.is_shared):
        raise HTTPException(404, "Preset not found")
    for field in ("name", "workspace_kind", "queue_group_id", "layout",
                  "is_default", "is_shared"):
        v = getattr(payload, field, None)
        if v is not None:
            setattr(p, field, v)
    await db.commit()
    await db.refresh(p)
    return _preset_to_dict(p)


@router.delete("/presets/{preset_id}")
async def delete_preset(
    preset_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p = await db.get(DashboardPreset, preset_id)
    if not p or (p.user_id != user.id and not p.is_shared):
        raise HTTPException(404, "Preset not found")
    await db.delete(p)
    await db.commit()
    return {"deleted": str(preset_id)}


@router.post("/presets/{preset_id}/default")
async def mark_preset_default(
    preset_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p = await db.get(DashboardPreset, preset_id)
    if not p or (p.user_id != user.id and not p.is_shared):
        raise HTTPException(404, "Preset not found")
    await db.execute(text("""
        UPDATE dashboard_presets SET is_default = false WHERE user_id = :uid
    """), {"uid": str(user.id)})
    p.is_default = True
    await db.commit()
    return _preset_to_dict(p)
