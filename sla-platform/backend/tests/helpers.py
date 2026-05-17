"""Shared test helpers — functions, not fixtures.

Import from here instead of conftest to avoid module resolution issues.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from app.core.database import sync_session_factory
from app.core.security import create_access_token, get_password_hash
from app.domain.models import AuditLog, ImportSession, RefreshToken, Team, User


def admin_token() -> str:
    """Get token for the seeded admin user."""
    return _token_for("admin", "admin")


def _token_for(email: str, role: str) -> str:
    session = sync_session_factory()
    try:
        user = session.query(User).filter(User.email == email).first()
        if user:
            return create_access_token(user.id, user.role)
        return ""
    finally:
        session.close()


def create_user(
    email: str,
    role: str = "viewer",
    password: str = "test123",
    display_name: str = "Test User",
) -> User:
    session = sync_session_factory()
    try:
        existing = session.query(User).filter(User.email == email).first()
        if existing:
            return existing
        user = User(
            email=email,
            display_name=display_name,
            password_hash=get_password_hash(password),
            role=role,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    finally:
        session.close()


def cleanup_users(emails: list[str]) -> None:
    session = sync_session_factory()
    try:
        ids = [
            r[0]
            for e in emails
            for r in session.query(User.id).filter(User.email == e).all()
        ]
        if not ids:
            return
        session.query(AuditLog).filter(AuditLog.actor_id.in_(ids)).delete(
            synchronize_session=False
        )
        session.query(RefreshToken).filter(
            RefreshToken.user_id.in_(ids)
        ).delete(synchronize_session=False)
        session.query(User).filter(User.id.in_(ids)).delete(
            synchronize_session=False
        )
        session.commit()
    finally:
        session.close()


def create_team(
    name: str = "Test Team",
    queue_prefix: str = "TT",
    description: Optional[str] = None,
) -> Team:
    session = sync_session_factory()
    try:
        team = Team(name=name, queue_prefix=queue_prefix, description=description)
        session.add(team)
        session.commit()
        session.refresh(team)
        return team
    finally:
        session.close()


def create_import_session(status: str = "draft") -> ImportSession:
    session = sync_session_factory()
    try:
        imp = ImportSession(status=status)
        session.add(imp)
        session.commit()
        session.refresh(imp)
        return imp
    finally:
        session.close()


def cleanup_imports() -> None:
    session = sync_session_factory()
    try:
        session.query(ImportSession).delete()
        session.commit()
    finally:
        session.close()
