"""Tests for authentication and RBAC system.

Run with: docker compose exec backend pytest tests/test_auth.py -v
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.database import sync_session_factory
from app.core.security import create_access_token, create_refresh_token, get_password_hash
from app.domain.models import User, RefreshToken, AuditLog

pytestmark = pytest.mark.asyncio

# Real HTTP requests to the running uvicorn server (same container, port 8000)
BASE_URL = "http://localhost:8000"


# ---------------------------------------------------------------------------
# Sync DB helpers — each test creates its own data and cleans up afterward
# ---------------------------------------------------------------------------


def _create_user(email, role="viewer", password="test123", display_name="Test User"):
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


def _cleanup_users(emails):
    session = sync_session_factory()
    try:
        user_ids = [
            row[0] for email in emails
            for row in session.query(User.id).filter(User.email == email).all()
        ]
        if not user_ids:
            return
        session.query(AuditLog).filter(
            AuditLog.actor_id.in_(user_ids)
        ).delete(synchronize_session=False)
        session.query(RefreshToken).filter(
            RefreshToken.user_id.in_(user_ids)
        ).delete(synchronize_session=False)
        session.query(User).filter(User.id.in_(user_ids)).delete(
            synchronize_session=False
        )
        session.commit()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(base_url=BASE_URL) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_health_public(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


async def test_login_missing_fields(client):
    resp = await client.post("/api/v1/auth/login", json={})
    assert resp.status_code == 422


async def test_login_wrong_password(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin", "password": "wrongpass"},
    )
    assert resp.status_code == 401


async def test_me_unauthenticated(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_protected_route_requires_auth(client):
    routes = [
        "/api/v1/dashboards/overview?days=30",
        "/api/v1/tickets",
        "/api/v1/imports/sessions",
        "/api/v1/sla/definitions",
        "/api/v1/teams",
        "/api/v1/reports",
        "/api/v1/audit/log",
    ]
    for route in routes:
        resp = await client.get(route)
        assert resp.status_code == 401, f"{route} should require auth"


async def test_me_with_token(client):
    user = _create_user("me_test@test.com", role="viewer")
    token = create_access_token(user.id, user.role)
    try:
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == user.email
        assert data["role"] == user.role
        assert data["id"] == str(user.id)
    finally:
        _cleanup_users(["me_test@test.com"])


async def test_login_and_access(client):
    _create_user("login_test@test.com", role="viewer", password="testpass")
    try:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "login_test@test.com", "password": "testpass"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

        me_resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {data['access_token']}"},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "login_test@test.com"
    finally:
        _cleanup_users(["login_test@test.com"])


async def test_refresh_token_rotation(client):
    user = _create_user("refresh_test@test.com", role="viewer", password="testpass")
    session = sync_session_factory()
    try:
        token_id = uuid4()
        refresh_str = create_refresh_token(user.id, token_id)

        rt = RefreshToken(
            id=token_id,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        session.add(rt)
        session.commit()

        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_str},
        )
        assert resp.status_code == 200
        new_tokens = resp.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens

        check = sync_session_factory()
        try:
            old_token = check.get(RefreshToken, token_id)
            assert old_token is not None
            assert old_token.revoked_at is not None
        finally:
            check.close()

        old_resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_str},
        )
        assert old_resp.status_code == 401
    finally:
        session.close()
        _cleanup_users(["refresh_test@test.com"])


async def test_logout_revokes_tokens(client):
    user = _create_user("logout_test@test.com", role="viewer", password="testpass")
    session = sync_session_factory()
    try:
        token = create_access_token(user.id, user.role)

        rt1 = RefreshToken(
            id=uuid4(), user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        rt2 = RefreshToken(
            id=uuid4(), user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        session.add(rt1)
        session.add(rt2)
        session.commit()

        resp = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

        remaining = session.query(RefreshToken).filter(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        ).all()
        assert len(remaining) == 0
    finally:
        session.close()
        _cleanup_users(["logout_test@test.com"])


async def test_admin_only_endpoints(client):
    user = _create_user("viewer_rbac@test.com", role="viewer", password="testpass")
    token = create_access_token(user.id, user.role)
    try:
        admin_routes = [
            ("GET", "/api/v1/auth/users"),
            ("POST", "/api/v1/auth/users"),
        ]
        for method, path in admin_routes:
            if method == "GET":
                resp = await client.get(path, headers={"Authorization": f"Bearer {token}"})
            else:
                resp = await client.post(path, headers={"Authorization": f"Bearer {token}"}, json={})
            assert resp.status_code == 403, f"{method} {path} should be admin-only"
    finally:
        _cleanup_users(["viewer_rbac@test.com"])


async def test_admin_can_create_user(client):
    _cleanup_users(["newguy@test.com", "admin_crud@test.com"])
    user = _create_user("admin_crud@test.com", role="admin", password="testpass")
    token = create_access_token(user.id, user.role)
    try:
        resp = await client.post(
            "/api/v1/auth/users",
            json={
                "email": "newguy@test.com",
                "display_name": "New Guy",
                "password": "newpass123",
                "role": "analyst",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "newguy@test.com"
        assert data["role"] == "analyst"
        assert data["is_active"] is True
    finally:
        _cleanup_users(["admin_crud@test.com", "newguy@test.com"])


async def test_create_duplicate_email(client):
    _create_user("dupadmin@test.com", role="admin", password="testpass")
    user = _create_user("dupadmintwo@test.com", role="admin", password="testpass")
    token = create_access_token(user.id, user.role)
    try:
        resp = await client.post(
            "/api/v1/auth/users",
            json={
                "email": "dupadmin@test.com",
                "display_name": "Duplicate",
                "password": "test123",
                "role": "viewer",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409
    finally:
        _cleanup_users(["dupadmin@test.com", "dupadmintwo@test.com"])
