from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.domain.models import User
from app.domain.schemas import (
    LoginRequest,
    MeResponse,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services.audit_service import AuditService
from app.services.user_service import UserService

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await UserService.authenticate(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token, refresh_token, token_obj = await UserService.create_tokens(db, user)
    await db.commit()

    AuditService.log_sync(
        action="login",
        actor_id=user.id,
        details={"email": user.email},
        ip_address=request.client.host if request.client else None,
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await UserService.refresh_tokens(db, payload.refresh_token)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    access_token, refresh_token, _ = result
    await db.commit()

    AuditService.log_sync(
        action="token_refresh",
        ip_address=request.client.host if request.client else None,
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=MeResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )


@router.post("/logout", response_model=dict)
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await UserService.revoke_user_tokens(db, current_user.id)
    await db.commit()

    AuditService.log_sync(
        action="logout",
        actor_id=current_user.id,
    )

    return {"message": "Logged out successfully"}


@router.get("/users", response_model=dict)
async def list_users(
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    users, total = await UserService.list_users(db, limit=limit, offset=offset)
    return {
        "users": [UserResponse.model_validate(u) for u in users],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/users", response_model=UserResponse)
async def create_user(
    payload: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    existing = await UserService.get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = await UserService.create_user(
        db,
        email=payload.email,
        display_name=payload.display_name,
        password=payload.password,
        role=payload.role,
    )
    await db.commit()

    AuditService.log_sync(
        action="user_created",
        actor_id=current_user.id,
        resource_type="user",
        resource_id=str(user.id),
        details={"email": user.email, "role": user.role},
        ip_address=request.client.host if request.client else None,
    )

    return UserResponse.model_validate(user)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = await UserService.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = await UserService.update_user(
        db,
        user_id=user_id,
        email=payload.email,
        display_name=payload.display_name,
        password=payload.password,
        role=payload.role,
        is_active=payload.is_active,
    )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    await db.commit()

    AuditService.log_sync(
        action="user_updated",
        actor_id=current_user.id,
        resource_type="user",
        resource_id=str(user.id),
        ip_address=request.client.host if request.client else None,
    )

    return UserResponse.model_validate(user)


@router.delete("/users/{user_id}", response_model=dict)
async def delete_user(
    user_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    user = await UserService.update_user(db, user_id=user_id, is_active=False)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    await UserService.revoke_user_tokens(db, user_id)
    await db.commit()

    AuditService.log_sync(
        action="user_deactivated",
        actor_id=current_user.id,
        resource_type="user",
        resource_id=str(user_id),
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "User deactivated"}
