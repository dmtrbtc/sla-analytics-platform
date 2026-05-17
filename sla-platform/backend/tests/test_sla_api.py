"""Tests for SLA definition and metric API endpoints."""

import pytest

pytestmark = pytest.mark.asyncio

_VIEWER_EMAIL = "viewer_sla_api@test.com"
_VIEWER_PASS = "pass123"


async def _admin_headers(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _viewer_headers(client):
    """Ensure viewer user exists and return auth headers."""
    admin_h = await _admin_headers(client)
    resp = await client.post(
        "/api/v1/auth/users",
        json={"email": _VIEWER_EMAIL, "display_name": "Viewer", "password": _VIEWER_PASS, "role": "viewer"},
        headers=admin_h,
    )
    if resp.status_code == 409:
        pass
    else:
        assert resp.status_code == 201
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": _VIEWER_EMAIL, "password": _VIEWER_PASS},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# --- /sla/definitions ---

async def test_list_definitions_requires_auth(client):
    resp = await client.get("/api/v1/sla/definitions")
    assert resp.status_code == 401


async def test_list_definitions(client):
    headers = await _admin_headers(client)
    resp = await client.get("/api/v1/sla/definitions", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "definitions" in data


async def test_get_definition_requires_auth(client):
    resp = await client.get("/api/v1/sla/definitions/1")
    assert resp.status_code == 401


async def test_get_definition_not_found(client):
    headers = await _admin_headers(client)
    resp = await client.get("/api/v1/sla/definitions/99999", headers=headers)
    assert resp.status_code == 404


async def test_create_definition_requires_admin(client):
    headers = await _viewer_headers(client)
    resp = await client.post(
        "/api/v1/sla/definitions",
        json={"name": "Fail", "metric_type": "response_time", "warning_seconds": 3600, "critical_seconds": 86400},
        headers=headers,
    )
    assert resp.status_code == 403


async def test_create_definition(client):
    headers = await _admin_headers(client)
    resp = await client.post(
        "/api/v1/sla/definitions",
        json={
            "name": "Critical Response",
            "metric_type": "response_time",
            "warning_seconds": 3600,
            "critical_seconds": 86400,
            "queue_pattern": "Support*",
            "priority": "critical",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Critical Response"
    assert data["warning_seconds"] == 3600
    assert data["critical_seconds"] == 86400
    assert data["is_active"] is True


async def test_create_definition_missing_fields(client):
    headers = await _admin_headers(client)
    resp = await client.post(
        "/api/v1/sla/definitions",
        json={"name": "Incomplete"},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_update_definition_requires_admin(client):
    headers = await _viewer_headers(client)
    resp = await client.put(
        "/api/v1/sla/definitions/1",
        json={"name": "Hacked"},
        headers=headers,
    )
    assert resp.status_code == 403


async def test_update_definition(client):
    headers = await _admin_headers(client)
    resp = await client.post(
        "/api/v1/sla/definitions",
        json={"name": "To Update", "metric_type": "resolution_time", "warning_seconds": 7200, "critical_seconds": 172800},
        headers=headers,
    )
    assert resp.status_code == 201
    def_id = resp.json()["id"]

    resp2 = await client.put(
        f"/api/v1/sla/definitions/{def_id}",
        json={"name": "Updated Name", "warning_seconds": 14400},
        headers=headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["name"] == "Updated Name"
    assert resp2.json()["warning_seconds"] == 14400


async def test_delete_definition_requires_admin(client):
    headers = await _viewer_headers(client)
    resp = await client.delete("/api/v1/sla/definitions/1", headers=headers)
    assert resp.status_code == 403


async def test_delete_definition(client):
    headers = await _admin_headers(client)
    resp = await client.post(
        "/api/v1/sla/definitions",
        json={"name": "To Delete", "metric_type": "response_time", "warning_seconds": 3600, "critical_seconds": 86400},
        headers=headers,
    )
    assert resp.status_code == 201
    def_id = resp.json()["id"]

    resp2 = await client.delete(f"/api/v1/sla/definitions/{def_id}", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "deleted"

    resp3 = await client.get(f"/api/v1/sla/definitions/{def_id}", headers=headers)
    assert resp3.status_code == 404


# --- /sla/metrics ---

async def test_list_metrics_requires_auth(client):
    resp = await client.get("/api/v1/sla/metrics")
    assert resp.status_code == 401


async def test_list_metrics(client):
    headers = await _admin_headers(client)
    resp = await client.get("/api/v1/sla/metrics", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "metrics" in data
    assert "total" in data


async def test_list_metrics_with_filters(client):
    headers = await _admin_headers(client)
    resp = await client.get(
        "/api/v1/sla/metrics?metric_name=response_time&limit=5",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["metrics"]) <= 5


# --- /sla/breaches ---

async def test_list_breaches_requires_auth(client):
    resp = await client.get("/api/v1/sla/breaches")
    assert resp.status_code == 401


async def test_list_breaches(client):
    headers = await _admin_headers(client)
    resp = await client.get("/api/v1/sla/breaches", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "breaches" in data
    assert "total" in data


# --- /sla/summary ---

async def test_summary_requires_auth(client):
    resp = await client.get("/api/v1/sla/summary")
    assert resp.status_code == 401


async def test_summary(client):
    headers = await _admin_headers(client)
    resp = await client.get("/api/v1/sla/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_metrics" in data
    assert "total_breached" in data
    assert "breach_rate" in data
