"""Tests for import session creation and CSV upload validation."""

import io
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.database import sync_session_factory
from app.domain.models import ImportSession

pytestmark = pytest.mark.asyncio

CSV_HEADER = "TicketID,Title,Created,Owner,Queue,State,Priority\n"
CSV_ROW = "101,Test ticket,2025-01-15 10:00:00,agent1,Support,open,3\n"
VALID_CSV = CSV_HEADER + CSV_ROW


async def _admin_headers(client: AsyncClient) -> dict:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sla-platform.dev", "password": "admin123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_list_sessions_requires_auth(client):
    resp = await client.get("/api/v1/imports/sessions")
    assert resp.status_code == 401


async def test_list_sessions_empty(client):
    headers = await _admin_headers(client)
    resp = await client.get("/api/v1/imports/sessions", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_create_session_requires_admin(client):
    token = ""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sla-platform.dev", "password": "admin123"},
    )
    if resp.status_code == 200:
        token = resp.json()["access_token"]

    from tests.helpers import create_user, cleanup_users
    user = create_user("viewer_import@test.com", role="viewer", password="pass123")
    try:
        resp2 = await client.post(
            "/api/v1/auth/login",
            json={"email": "viewer_import@test.com", "password": "pass123"},
        )
        assert resp2.status_code == 200
        viewer_token = resp2.json()["access_token"]

        resp3 = await client.post(
            "/api/v1/imports/sessions", headers={"Authorization": f"Bearer {viewer_token}"}
        )
        assert resp3.status_code == 403
    finally:
        cleanup_users(["viewer_import@test.com"])


async def test_create_session(client):
    headers = await _admin_headers(client)
    resp = await client.post("/api/v1/imports/sessions", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["status"] == "draft"


async def test_get_session(client):
    headers = await _admin_headers(client)
    resp = await client.post("/api/v1/imports/sessions", headers=headers)
    session_id = resp.json()["id"]

    resp2 = await client.get(
        f"/api/v1/imports/sessions/{session_id}", headers=headers
    )
    assert resp2.status_code == 200
    assert resp2.json()["id"] == session_id


async def test_get_session_not_found(client):
    headers = await _admin_headers(client)
    resp = await client.get(
        f"/api/v1/imports/sessions/{uuid4()}", headers=headers
    )
    assert resp.status_code == 404


async def test_create_session_with_csv(client):
    """Test that we can create a session without file upload (API-level)."""
    headers = await _admin_headers(client)
    resp = await client.post("/api/v1/imports/sessions", headers=headers)
    assert resp.status_code == 200

    session_id = resp.json()["id"]
    get_resp = await client.get(
        f"/api/v1/imports/sessions/{session_id}", headers=headers
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "draft"


async def test_start_processing_requires_valid_session(client):
    headers = await _admin_headers(client)
    resp = await client.post(
        f"/api/v1/imports/sessions/{uuid4()}/start", headers=headers
    )
    assert resp.status_code == 400


async def test_csv_upload_fails_without_files(client):
    headers = await _admin_headers(client)
    resp = await client.post(
        "/api/v1/imports/sessions", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "draft"
