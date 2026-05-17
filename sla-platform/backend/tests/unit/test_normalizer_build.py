"""Unit tests for normalizer_service.py — _build_normalized logic.

This is a pure function: given raw_event dicts, returns normalized ticket_events.
"""

from datetime import datetime
from uuid import uuid4

from app.services.normalizer_service import NormalizerService


def _raw_event(overrides: dict | None = None) -> dict:
    base = {
        "ticket_number": "20250101-1001",
        "event_time": datetime(2025, 1, 6, 10, 0, 0),
        "event_name": "OwnerUpdate",
        "queue_name": "Support",
        "state_name": "open",
        "event_owner_name": "agent@test.dev",
        "src_queue": None,
        "dest_queue": None,
        "old_state": None,
        "new_state": None,
        "new_owner": "agent@test.dev",
        "old_owner": None,
        "pending_until": None,
        "duplicate_key": "key1",
        "event_raw_name": "%%agent@test.dev%%1%%",
        "id": 1,
    }
    if overrides:
        base.update(overrides)
    return base


def test_single_owner_update():
    events = [_raw_event()]
    result = NormalizerService._build_normalized(1001, events, uuid4())
    assert len(result) == 1
    assert result[0]["ticket_id"] == 1001
    assert result[0]["event_type"] == "OwnerUpdate"
    assert result[0]["owner_name"] == "agent@test.dev"
    assert result[0]["event_seq"] == 1


def test_owner_tracking():
    ev1 = _raw_event(dict(event_name="OwnerUpdate", new_owner="agent1", event_owner_name="agent1", id=1, duplicate_key="k1"))
    ev2 = _raw_event(dict(event_name="OwnerUpdate", new_owner="agent2", event_owner_name="agent2", id=2, duplicate_key="k2", event_time=datetime(2025, 1, 6, 11, 0, 0)))
    result = NormalizerService._build_normalized(1001, [ev1, ev2], uuid4())
    assert len(result) == 2
    assert result[0]["owner_name"] == "agent1"
    assert result[0]["old_owner"] is None
    assert result[1]["owner_name"] == "agent2"
    assert result[1]["old_owner"] == "agent1"


def test_lock_sets_owner():
    ev1 = _raw_event(dict(event_name="Lock", event_owner_name="agent1", id=1, duplicate_key="k1"))
    result = NormalizerService._build_normalized(1001, [ev1], uuid4())
    assert result[0]["owner_name"] == "agent1"


def test_lock_root_does_not_change_owner():
    ev1 = _raw_event(dict(event_name="OwnerUpdate", new_owner="agent1", event_owner_name="agent1", id=1, duplicate_key="k1"))
    ev2 = _raw_event(dict(event_name="Lock", event_owner_name="root@localhost", id=2, duplicate_key="k2", event_time=datetime(2025, 1, 6, 11, 0, 0)))
    result = NormalizerService._build_normalized(1001, [ev1, ev2], uuid4())
    assert result[1]["owner_name"] == "agent1"


def test_move_sets_owner():
    ev1 = _raw_event(dict(event_name="Move", event_owner_name="agent1", dest_queue="Other", id=1, duplicate_key="k1"))
    result = NormalizerService._build_normalized(1001, [ev1], uuid4())
    assert result[0]["owner_name"] == "agent1"


def test_move_root_does_not_change_owner():
    ev1 = _raw_event(dict(event_name="OwnerUpdate", new_owner="agent1", event_owner_name="agent1", id=1, duplicate_key="k1"))
    ev2 = _raw_event(dict(event_name="Move", dest_queue="Other", event_owner_name="root@localhost", id=2, duplicate_key="k2", event_time=datetime(2025, 1, 6, 11, 0, 0)))
    result = NormalizerService._build_normalized(1001, [ev1, ev2], uuid4())
    assert result[1]["owner_name"] == "agent1"


def test_system_action_true():
    ev = _raw_event(dict(event_owner_name="root@localhost"))
    result = NormalizerService._build_normalized(1001, [ev], uuid4())
    assert result[0]["is_system_action"] is True


def test_system_action_false():
    ev = _raw_event(dict(event_owner_name="agent@test.dev"))
    result = NormalizerService._build_normalized(1001, [ev], uuid4())
    assert result[0]["is_system_action"] is False


def test_event_seq_increments():
    events = [
        _raw_event(dict(id=1, duplicate_key="k1")),
        _raw_event(dict(id=2, duplicate_key="k2", event_time=datetime(2025, 1, 6, 11, 0, 0))),
        _raw_event(dict(id=3, duplicate_key="k3", event_time=datetime(2025, 1, 6, 12, 0, 0))),
    ]
    result = NormalizerService._build_normalized(1001, events, uuid4())
    assert [e["event_seq"] for e in result] == [1, 2, 3]


def test_ticket_number_carried_through():
    ev = _raw_event(dict(ticket_number="TKT-1001"))
    result = NormalizerService._build_normalized(1001, [ev], uuid4())
    assert result[0]["ticket_number"] == "TKT-1001"


def test_empty_events():
    result = NormalizerService._build_normalized(1001, [], uuid4())
    assert result == []


def test_is_system_action_none_owner():
    ev = _raw_event(dict(event_owner_name=None))
    result = NormalizerService._build_normalized(1001, [ev], uuid4())
    assert result[0]["is_system_action"] is True


def test_owner_name_fallback():
    """owner_name should be current_owner or event_owner_name."""
    ev = _raw_event(dict(event_owner_name="fallback@test.dev", new_owner=None))
    result = NormalizerService._build_normalized(1001, [ev], uuid4())
    assert result[0]["owner_name"] == "fallback@test.dev"


def test_pending_until_carried():
    dt = datetime(2025, 1, 10, 14, 0, 0)
    ev = _raw_event(dict(pending_until=dt))
    result = NormalizerService._build_normalized(1001, [ev], uuid4())
    assert result[0]["pending_until"] == dt


def test_queue_state_fields():
    ev = _raw_event(dict(queue_name="IT-Support", state_name="pending auto"))
    result = NormalizerService._build_normalized(1001, [ev], uuid4())
    assert result[0]["queue_name"] == "IT-Support"
    assert result[0]["state_name"] == "pending auto"
