"""Tests for team CRUD endpoints."""

import pytest

from tests.helpers import create_team, create_user, cleanup_users

pytestmark = pytest.mark.asyncio


async def _admin_headers(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sla-platform.dev", "password": "admin123"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _viewer_headers(client):
    user = create_user("viewer_team@test.com", role="viewer", password="pass123")
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "viewer_team@test.com", "password": "pass123"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_list_teams_requires_auth(client):
    resp = await client.get("/api/v1/teams")
    assert resp.status_code == 401


async def test_list_teams(client):
    headers = await _admin_headers(client)
    resp = await client.get("/api/v1/teams", headers=headers)
    assert resp.status_code == 200
    assert "teams" in resp.json()


async def test_create_team_requires_admin(client):
    headers = await _viewer_headers(client)
    try:
        resp = await client.post(
            "/api/v1/teams",
            json={"name": "Should Fail", "queue_prefix": "SF"},
            headers=headers,
        )
        assert resp.status_code == 403
    finally:
        cleanup_users(["viewer_team@test.com"])


async def test_update_team_requires_admin(client):
    headers = await _viewer_headers(client)
    try:
        resp = await client.put(
            "/api/v1/teams/1",
            json={"name": "Hacked"},
            headers=headers,
        )
        assert resp.status_code == 403
    finally:
        cleanup_users(["viewer_team@test.com"])


async def test_delete_team_requires_admin(client):
    headers = await _viewer_headers(client)
    try:
        resp = await client.delete(
            "/api/v1/teams/1",
            headers=headers,
        )
        assert resp.status_code == 403
    finally:
        cleanup_users(["viewer_team@test.com"])


async def test_create_team(client):
    headers = await _admin_headers(client)
    resp = await client.post(
        "/api/v1/teams",
        json={"name": "Support Team", "queue_prefix": "ST", "description": "Test"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Support Team"
    assert data["queue_prefix"] == "ST"


async def test_create_team_missing_fields(client):
    headers = await _admin_headers(client)
    resp = await client.post(
        "/api/v1/teams",
        json={"name": "Incomplete"},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_get_team(client):
    headers = await _admin_headers(client)
    team = create_team(name="Get Test", queue_prefix="GT")
    try:
        resp = await client.get(f"/api/v1/teams/{team.id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Get Test"
    finally:
        from app.core.database import sync_session_factory
        session = sync_session_factory()
        session.query(type(team)).filter(type(team).id == team.id).delete()
        session.commit()
        session.close()
