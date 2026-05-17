"""Tests for seed_admin_user — verifies deterministic credential creation/update.

Run inside Docker: docker compose exec backend pytest tests/test_seeds.py -v
"""

import pytest

from app.core.database import sync_session_factory
from app.core.security import get_password_hash, verify_password
from app.domain.models import AuditLog, RefreshToken, User
from app.seeds import ADMIN_EMAIL, ADMIN_PASSWORD, seed_admin_user

pytestmark = pytest.mark.integration


def _cleanup():
    session = sync_session_factory()
    try:
        user = session.query(User).filter(User.email == ADMIN_EMAIL).first()
        if user is not None:
            session.query(AuditLog).filter(AuditLog.actor_id == user.id).delete(
                synchronize_session=False
            )
            session.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete(
                synchronize_session=False
            )
            session.delete(user)
            session.commit()
    finally:
        session.close()


def test_seed_creates_admin_when_missing():
    _cleanup()
    seed_admin_user()
    session = sync_session_factory()
    try:
        user = session.query(User).filter(User.email == ADMIN_EMAIL).first()
        assert user is not None
        assert user.email == ADMIN_EMAIL
        assert verify_password(ADMIN_PASSWORD, user.password_hash)
        assert user.role == "admin"
        assert user.is_active is True
    finally:
        session.close()


def test_seed_updates_password_hash():
    _cleanup()
    session = sync_session_factory()
    try:
        user = User(
            email=ADMIN_EMAIL,
            display_name="Admin",
            password_hash=get_password_hash("oldpassword"),
            role="admin",
        )
        session.add(user)
        session.commit()
    finally:
        session.close()

    seed_admin_user()

    session2 = sync_session_factory()
    try:
        user = session2.query(User).filter(User.email == ADMIN_EMAIL).first()
        assert user is not None
        assert verify_password(ADMIN_PASSWORD, user.password_hash)
        assert not verify_password("oldpassword", user.password_hash)
    finally:
        session2.close()


def test_seed_fixes_wrong_role():
    _cleanup()
    session = sync_session_factory()
    try:
        user = User(
            email=ADMIN_EMAIL,
            display_name="Admin",
            password_hash=get_password_hash(ADMIN_PASSWORD),
            role="viewer",
        )
        session.add(user)
        session.commit()
    finally:
        session.close()

    seed_admin_user()

    session2 = sync_session_factory()
    try:
        user = session2.query(User).filter(User.email == ADMIN_EMAIL).first()
        assert user.role == "admin"
    finally:
        session2.close()


def test_seed_reactivates_inactive_admin():
    _cleanup()
    session = sync_session_factory()
    try:
        user = User(
            email=ADMIN_EMAIL,
            display_name="Admin",
            password_hash=get_password_hash(ADMIN_PASSWORD),
            role="admin",
            is_active=False,
        )
        session.add(user)
        session.commit()
    finally:
        session.close()

    seed_admin_user()

    session2 = sync_session_factory()
    try:
        user = session2.query(User).filter(User.email == ADMIN_EMAIL).first()
        assert user.is_active is True
    finally:
        session2.close()


def test_seed_idempotent_rerun():
    _cleanup()
    seed_admin_user()
    seed_admin_user()
    session = sync_session_factory()
    try:
        count = session.query(User).filter(User.email == ADMIN_EMAIL).count()
        assert count == 1
    finally:
        session.close()


def test_admin_login_after_seed():
    """Full end-to-end — seed creates admin, then API login succeeds."""
    _cleanup()
    seed_admin_user()
    import httpx
    resp = httpx.post(
        "http://localhost:8000/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
