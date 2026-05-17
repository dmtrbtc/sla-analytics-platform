"""Unit tests for pause_engine.py — pause segment computation.

These tests use SQLAlchemy with aiosqlite for fast in-memory DB testing.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.models import Base, TicketEvent
from app.services.sla.pause_engine import (
    PENDING_STATES,
    calculate_active_time,
    compute_pause_segments,
)

IMPORT_ID = uuid4()


@pytest.fixture
def db_session():
    engine = create_engine("sqlite://", echo=False)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


_event_id_counter = 0


def _event(**kw) -> TicketEvent:
    global _event_id_counter
    _event_id_counter += 1
    defaults = dict(
        id=_event_id_counter,
        ticket_id=1001, ticket_number="T-1001", event_seq=1,
        event_time=datetime(2025, 1, 6, 10, 0, 0),
        event_type="OwnerUpdate", queue_name="Support",
        state_name="open", owner_name="agent",
        is_system_action=False, import_id=IMPORT_ID,
        raw_event_id=_event_id_counter,
    )
    defaults.update(kw)
    return TicketEvent(**defaults)


def _commit(session, *events):
    for e in events:
        session.add(e)
    session.commit()


class TestPendingStates:
    def test_pending_states_are_frozen(self):
        assert isinstance(PENDING_STATES, frozenset)

    def test_known_pending_states(self):
        assert "pending auto" in PENDING_STATES
        assert "pending reminder" in PENDING_STATES
        assert "pending reopen" in PENDING_STATES
        assert "open" not in PENDING_STATES
        assert "closed successful" not in PENDING_STATES


class TestComputePauseSegments:
    def test_no_pending_states(self, db_session):
        _commit(db_session,
            _event(event_seq=1, event_type="OwnerUpdate", state_name="open"),
            _event(event_seq=2, event_type="Move", state_name="open", dest_queue="Other"),
        )
        pauses = compute_pause_segments(db_session, 1001, IMPORT_ID.hex)
        assert pauses == []

    def test_single_pause_segment(self, db_session):
        _commit(db_session,
            _event(event_seq=1, event_type="OwnerUpdate", state_name="open"),
            _event(event_seq=2, event_type="StateUpdate", state_name="pending auto", new_state="pending auto"),
            _event(event_seq=3, event_type="StateUpdate", state_name="open", new_state="open"),
        )
        pauses = compute_pause_segments(db_session, 1001, IMPORT_ID.hex)
        assert len(pauses) == 1
        assert pauses[0][1] > pauses[0][0]

    def test_multiple_pause_segments(self, db_session):
        _commit(db_session,
            _event(event_seq=1, state_name="open"),
            _event(event_seq=2, state_name="pending auto"),
            _event(event_seq=3, state_name="open"),
            _event(event_seq=4, state_name="pending reminder"),
            _event(event_seq=5, state_name="closed successful"),
        )
        pauses = compute_pause_segments(db_session, 1001, IMPORT_ID.hex)
        assert len(pauses) == 2

    def test_no_pause_if_never_enters_pending(self, db_session):
        _commit(db_session,
            _event(event_seq=1, state_name="open"),
            _event(event_seq=2, state_name="closed successful"),
        )
        pauses = compute_pause_segments(db_session, 1001, IMPORT_ID.hex)
        assert pauses == []

    def test_set_pending_time_triggers_pause(self, db_session):
        _commit(db_session,
            _event(event_seq=1, state_name="open"),
            _event(event_seq=2, event_type="SetPendingTime", state_name="open", pending_until=datetime(2025, 1, 7, 10, 0, 0)),
            _event(event_seq=3, event_type="OwnerUpdate", state_name="open"),
        )
        pauses = compute_pause_segments(db_session, 1001, IMPORT_ID.hex)
        assert len(pauses) == 1

    def test_pending_until_none_does_not_pause(self, db_session):
        _commit(db_session,
            _event(event_seq=1, state_name="open"),
            _event(event_seq=2, event_type="SetPendingTime", state_name="open", pending_until=None),
        )
        pauses = compute_pause_segments(db_session, 1001, IMPORT_ID.hex)
        assert pauses == []

    def test_in_pending_at_end(self, db_session):
        _commit(db_session,
            _event(event_seq=1, state_name="open"),
            _event(event_seq=2, state_name="pending auto"),
        )
        pauses = compute_pause_segments(db_session, 1001, IMPORT_ID.hex)
        assert len(pauses) == 1

    def test_ticket_with_no_events(self, db_session):
        pauses = compute_pause_segments(db_session, 9999, IMPORT_ID.hex)
        assert pauses == []


class TestCalculateActiveTime:
    def test_no_pauses_all_active(self, db_session):
        period = (datetime(2025, 1, 6, 10, 0, 0), datetime(2025, 1, 6, 12, 0, 0))
        result = calculate_active_time(db_session, 1001, IMPORT_ID.hex, [period])
        assert result["active_time_seconds"] == 7200
        assert result["paused_time_seconds"] == 0
        assert len(result["segments"]) == 1

    def test_active_with_pause(self, db_session):
        _commit(db_session,
            _event(event_seq=1, state_name="open", event_time=datetime(2025, 1, 6, 10, 0, 0)),
            _event(event_seq=2, state_name="pending auto", event_time=datetime(2025, 1, 6, 10, 30, 0)),
            _event(event_seq=3, state_name="open", event_time=datetime(2025, 1, 6, 11, 0, 0)),
        )
        period = (datetime(2025, 1, 6, 10, 0, 0), datetime(2025, 1, 6, 12, 0, 0))
        result = calculate_active_time(db_session, 1001, IMPORT_ID.hex, [period])
        assert result["active_time_seconds"] == 5400
        assert result["paused_time_seconds"] == 1800

    def test_multiple_periods(self, db_session):
        _commit(db_session,
            _event(event_seq=1, state_name="pending auto", event_time=datetime(2025, 1, 6, 11, 0, 0)),
            _event(event_seq=2, state_name="open", event_time=datetime(2025, 1, 6, 12, 0, 0)),
        )
        periods = [
            (datetime(2025, 1, 6, 10, 0, 0), datetime(2025, 1, 6, 11, 0, 0)),
            (datetime(2025, 1, 6, 12, 0, 0), datetime(2025, 1, 6, 13, 0, 0)),
        ]
        result = calculate_active_time(db_session, 1001, IMPORT_ID.hex, periods)
        assert result["active_time_seconds"] == 7200
        assert result["paused_time_seconds"] == 0

    def test_business_hours_config(self, db_session):
        period = (datetime(2025, 1, 10, 17, 0, 0), datetime(2025, 1, 13, 10, 0, 0))
        result = calculate_active_time(
            db_session, 1001, IMPORT_ID.hex, [period],
            business_hours_config={"24_7": False},
        )
        assert result["active_time_seconds"] == 7200
