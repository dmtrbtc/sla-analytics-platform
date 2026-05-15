"""Tests for report generation endpoints."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_report_generate_requires_auth(client):
    resp = await client.post("/api/v1/reports/generate?report_type=sla_breaches")
    assert resp.status_code == 401


async def test_report_generate_requires_admin(client):
    from tests.helpers import create_user, cleanup_users

    user = create_user("viewer_report@test.com", role="viewer", password="pass123")
    try:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "viewer_report@test.com", "password": "pass123"},
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp2 = await client.post(
            "/api/v1/reports/generate?report_type=sla_breaches", headers=headers
        )
        assert resp2.status_code == 403
    finally:
        cleanup_users(["viewer_report@test.com"])


async def test_report_list_requires_auth(client):
    resp = await client.get("/api/v1/reports")
    assert resp.status_code == 401


async def test_report_status_requires_auth(client):
    resp = await client.get("/api/v1/reports/status/fake-task-id")
    assert resp.status_code == 401


async def test_report_download_requires_auth(client):
    resp = await client.get("/api/v1/reports/fake-report.xlsx/download")
    assert resp.status_code == 401


async def test_report_generate_started(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sla-platform.dev", "password": "admin123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp2 = await client.post(
        "/api/v1/reports/generate?report_type=sla_breaches", headers=headers
    )
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["status"] == "started"
    assert "task_id" in data
