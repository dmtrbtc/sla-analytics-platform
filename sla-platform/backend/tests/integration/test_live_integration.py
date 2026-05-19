"""Live integration tests: WebSocket, dashboard, incidents E2E flow."""

import asyncio
import json

import pytest

pytestmark = pytest.mark.asyncio


async def _get_token(client) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


async def test_dashboard_overview_with_percentiles(client):
    """Dashboard overview returns percentiles alongside averages."""
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/v1/dashboards/overview?days=30", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "avg_response_time_seconds" in data
    assert "avg_resolution_time_seconds" in data
    assert "response_percentiles" in data
    assert "resolution_percentiles" in data

    for key in ("response_percentiles", "resolution_percentiles"):
        p = data[key]
        assert "avg" in p
        assert "p50" in p
        assert "p90" in p
        assert "p95" in p
        assert "p99" in p
        assert isinstance(p["avg"], (int, float))
        assert isinstance(p["p50"], (int, float))
        assert isinstance(p["p90"], (int, float))
        assert isinstance(p["p95"], (int, float))
        assert isinstance(p["p99"], (int, float))


async def test_analytics_overview_kpis(client):
    """Analytics overview returns operational KPIs."""
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/v1/analytics/overview?days=30", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    expected = [
        "tickets_at_risk", "overloaded_queues", "avg_wait_seconds",
        "avg_reassignments", "most_problematic_queue", "unowned_tickets",
    ]
    for key in expected:
        assert key in data, f"Missing key: {key}"


async def test_incidents_crud_flow(client):
    """Full incident lifecycle: detect, list, create, acknowledge, resolve, comment."""
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Auto-detect
    resp = await client.get("/api/v1/ops/incidents/detect", headers=headers)
    assert resp.status_code == 200
    detect = resp.json()
    assert "detected" in detect

    # List
    resp = await client.get("/api/v1/ops/incidents", headers=headers)
    assert resp.status_code == 200
    incidents = resp.json()
    assert isinstance(incidents, list)

    # Create
    create_resp = await client.post(
        "/api/v1/ops/incidents",
        headers=headers,
        json={
            "title": "Test Incident",
            "severity": "high",
            "incident_type": "sla_breach",
            "summary": "Integration test incident",
            "queue_name": "Support",
        },
    )
    assert create_resp.status_code == 200
    incident = create_resp.json()
    incident_id = incident.get("id")
    assert incident_id is not None

    # Get by ID
    get_resp = await client.get(
        f"/api/v1/ops/incidents/{incident_id}", headers=headers
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == incident_id

    # Acknowledge
    ack_resp = await client.post(
        f"/api/v1/ops/incidents/{incident_id}/acknowledge",
        headers=headers,
    )
    assert ack_resp.status_code == 200

    # Add comment
    comment_resp = await client.post(
        f"/api/v1/ops/incidents/{incident_id}/comments",
        headers=headers,
        json={"text": "Investigating..."},
    )
    assert comment_resp.status_code == 200

    # Resolve
    resolve_resp = await client.post(
        f"/api/v1/ops/incidents/{incident_id}/resolve",
        headers=headers,
    )
    assert resolve_resp.status_code == 200


async def test_ai_prediction_endpoint(client):
    """AI prediction returns structured risk assessment."""
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/v1/ai/anomalies", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_ai_staffing_endpoint(client):
    """AI staffing returns recommendations."""
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/v1/ai/staffing", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_ai_hints_endpoint(client):
    """AI hints returns root-cause analysis strings."""
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/v1/ai/hints", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_websocket_connect_and_receive(client):
    """WebSocket connects with token, subscribes, and receives events."""
    token = await _get_token(client)

    try:
        import websockets
    except ImportError:
        pytest.skip("websockets library not installed")

    async with websockets.connect(
        f"ws://localhost:8000/ws/dashboard?token={token}",
        max_size=2 ** 20,
        close_timeout=5,
    ) as ws:
        # Send subscribe
        await ws.send(json.dumps({"type": "subscribe", "channels": ["sla.breaches", "ops.alerts"]}))
        # Wait for pong or event
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(msg)
            assert "type" in data
        except asyncio.TimeoutError:
            pytest.fail("No message received within 5s")


async def test_websocket_auth_rejected(client):
    """WebSocket connection without valid token is rejected."""
    try:
        import websockets
    except ImportError:
        pytest.skip("websockets library not installed")

    with pytest.raises(websockets.exceptions.InvalidStatusCode):
        async with websockets.connect(
            "ws://localhost:8000/ws/dashboard?token=invalid",
            max_size=2 ** 20,
            close_timeout=5,
        ):
            pass


async def test_dashboard_time_series_endpoint(client):
    """Time-series endpoint returns data for response_time metric."""
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get(
        "/api/v1/dashboards/time-series?metric=response_time&granularity=daily&days=30",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_executive_report_generation(client):
    """Executive report endpoint can be triggered."""
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/reports/generate?report_type=executive&fmt=xlsx",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "started"
    assert data["report_type"] == "executive"
