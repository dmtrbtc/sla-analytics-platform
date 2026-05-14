from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.domain.models import RefreshToken, User


class UserService:

    @staticmethod
    async def authenticate(
        db: AsyncSession, email: str, password: str
    ) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            return None
        if not verify_password(password, user.password_hash):
            return None
        if not user.is_active:
            return None
        return user

    @staticmethod
    async def create_tokens(
        db: AsyncSession, user: User
    ) -> Tuple[str, str, RefreshToken]:
        token_id = uuid4()
        access_token = create_access_token(user.id, user.role)
        refresh_token_str = create_refresh_token(user.id, token_id)

        refresh_token = RefreshToken(
            id=token_id,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=30),
        )
        db.add(refresh_token)
        await db.flush()

        return access_token, refresh_token_str, refresh_token

    @staticmethod
    async def refresh_tokens(
        db: AsyncSession, refresh_token_str: str
    ) -> Optional[Tuple[str, str, RefreshToken]]:
        payload = decode_token(refresh_token_str)
        if payload is None:
            return None

        token_type = payload.get("type")
        if token_type != "refresh":
            return None

        token_id = payload.get("jti")
        user_id = payload.get("sub")
        if token_id is None or user_id is None:
            return None

        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.id == UUID(token_id),
                RefreshToken.user_id == UUID(user_id),
                RefreshToken.revoked_at.is_(None),
            )
        )
        token = result.scalar_one_or_none()
        if token is None:
            return None

        if token.expires_at < datetime.now(timezone.utc):
            return None

        token.revoked_at = datetime.now(timezone.utc)
        db.add(token)

        result = await db.execute(select(User).where(User.id == UUID(user_id)))
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            return None

        new_token_id = uuid4()
        new_access_token = create_access_token(user.id, user.role)
        new_refresh_token_str = create_refresh_token(user.id, new_token_id)

        new_token = RefreshToken(
            id=new_token_id,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=30),
        )
        db.add(new_token)
        await db.flush()

        return new_access_token, new_refresh_token_str, new_token

    @staticmethod
    async def revoke_user_tokens(db: AsyncSession, user_id: UUID) -> None:
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        tokens = result.scalars().all()
        now = datetime.now(timezone.utc)
        for t in tokens:
            t.revoked_at = now
            db.add(t)
        await db.flush()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
        return await db.get(User, user_id)

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_user(
        db: AsyncSession,
        email: str,
        display_name: str,
        password: str,
        role: str = "viewer",
    ) -> User:
        user = User(
            email=email,
            display_name=display_name,
            password_hash=get_password_hash(password),
            role=role,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def update_user(
        db: AsyncSession,
        user_id: UUID,
        email: Optional[str] = None,
        display_name: Optional[str] = None,
        password: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[User]:
        user = await db.get(User, user_id)
        if user is None:
            return None

        if email is not None:
            user.email = email
        if display_name is not None:
            user.display_name = display_name
        if password is not None:
            user.password_hash = get_password_hash(password)
        if role is not None:
            user.role = role
        if is_active is not None:
            user.is_active = is_active

        user.updated_at = datetime.now(timezone.utc)
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def list_users(
        db: AsyncSession,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[User], int]:
        count_q = select(func.count(User.id))
        total = (await db.execute(count_q)).scalar() or 0

        q = select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(q)
        users = result.scalars().all()

        return list(users), total
