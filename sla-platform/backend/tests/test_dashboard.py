"""Tests for dashboard aggregation endpoints."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_overview_requires_auth(client):
    resp = await client.get("/api/v1/dashboards/overview?days=30")
    assert resp.status_code == 401


async def test_overview_returns_structure(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp2 = await client.get(
        "/api/v1/dashboards/overview?days=30", headers=headers
    )
    assert resp2.status_code == 200
    data = resp2.json()
    assert "total_tickets" in data
    assert "open_tickets" in data
    assert "closed_tickets" in data


async def test_time_series_requires_auth(client):
    resp = await client.get("/api/v1/dashboards/time-series?days=30")
    assert resp.status_code == 401


async def test_time_series_returns_list(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp2 = await client.get(
        "/api/v1/dashboards/time-series?days=30", headers=headers
    )
    assert resp2.status_code == 200


async def test_teams_analytics_requires_auth(client):
    resp = await client.get("/api/v1/dashboards/teams?days=90")
    assert resp.status_code == 401


async def test_ticket_flow_requires_auth(client):
    resp = await client.get("/api/v1/dashboards/ticket-flow?days=90")
    assert resp.status_code == 401


async def test_sla_trend_requires_auth(client):
    resp = await client.get("/api/v1/dashboards/sla-trend")
    assert resp.status_code == 401
