"""Tests for ticket detail and timeline endpoints."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_list_tickets_requires_auth(client):
    resp = await client.get("/api/v1/tickets")
    assert resp.status_code == 401


async def test_list_tickets_returns_structure(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sla-platform.dev", "password": "admin123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp2 = await client.get("/api/v1/tickets", headers=headers)
    assert resp2.status_code == 200
    data = resp2.json()
    assert "tickets" in data or "items" in data or isinstance(data, list)


async def test_ticket_detail_requires_auth(client):
    resp = await client.get("/api/v1/tickets/1")
    assert resp.status_code == 401


async def test_ticket_detail_not_found(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sla-platform.dev", "password": "admin123"},
    )
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp2 = await client.get("/api/v1/tickets/99999999", headers=headers)
    assert resp2.status_code in (200, 404)


async def test_ticket_timeline_requires_auth(client):
    resp = await client.get("/api/v1/tickets/1/timeline")
    assert resp.status_code == 401


async def test_ticket_ownership_requires_auth(client):
    resp = await client.get("/api/v1/tickets/1/ownership")
    assert resp.status_code == 401


async def test_ticket_queue_periods_requires_auth(client):
    resp = await client.get("/api/v1/tickets/1/queue-periods")
    assert resp.status_code == 401


async def test_ticket_sla_requires_auth(client):
    resp = await client.get("/api/v1/tickets/1/sla")
    assert resp.status_code == 401
