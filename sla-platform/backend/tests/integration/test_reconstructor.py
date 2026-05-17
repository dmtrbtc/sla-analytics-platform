"""Unit tests for reconstructor_service.py — ownership/queue period reconstruction.

Uses in-memory SQLite for fast test DB.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.models import Base, OwnershipPeriod, QueuePeriod
from app.services.reconstructor_service import ReconstructorService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite://", echo=False)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def _ev(event_type: str, event_time: datetime, **kw) -> dict:
    base = dict(
        ticket_number="T-1001", title="Test",
        event_type=event_type, event_time=event_time,
        queue_name="Support", state_name="open",
        owner_name="agent@test.dev",
        dest_queue=None, new_owner=None, new_state=None,
    )
    base.update(kw)
    return base


class TestBuildOwnershipPeriods:
    def test_single_owner(self, db_session):
        events = [
            _ev("OwnerUpdate", datetime(2025, 1, 6, 10, 0, 0), new_owner="agent1"),
            _ev("OwnerUpdate", datetime(2025, 1, 6, 12, 0, 0), new_owner="agent1"),
        ]
        count = ReconstructorService._build_ownership_periods(db_session, 1001, events)
        assert count == 1
        periods = db_session.query(OwnershipPeriod).all()
        assert periods[0].owner == "agent1"

    def test_owner_change(self, db_session):
        events = [
            _ev("OwnerUpdate", datetime(2025, 1, 6, 10, 0, 0), new_owner="agent1"),
            _ev("OwnerUpdate", datetime(2025, 1, 6, 12, 0, 0), new_owner="agent2"),
        ]
        count = ReconstructorService._build_ownership_periods(db_session, 1001, events)
        assert count == 2
        periods = db_session.query(OwnershipPeriod).order_by(OwnershipPeriod.id).all()
        assert periods[0].owner == "agent1"
        assert periods[1].owner == "agent2"

    def test_no_owner_change(self, db_session):
        events = [
            _ev("OwnerUpdate", datetime(2025, 1, 6, 10, 0, 0), new_owner="agent1"),
            _ev("OwnerUpdate", datetime(2025, 1, 6, 12, 0, 0), new_owner="agent1"),
        ]
        count = ReconstructorService._build_ownership_periods(db_session, 1001, events)
        assert count == 1

    def test_no_owner_update_events(self, db_session):
        events = [
            _ev("StateUpdate", datetime(2025, 1, 6, 10, 0, 0)),
            _ev("StateUpdate", datetime(2025, 1, 6, 12, 0, 0)),
        ]
        count = ReconstructorService._build_ownership_periods(db_session, 1001, events)
        assert count == 0

    def test_owner_update_without_new_owner(self, db_session):
        events = [
            _ev("OwnerUpdate", datetime(2025, 1, 6, 10, 0, 0)),  # no new_owner
        ]
        count = ReconstructorService._build_ownership_periods(db_session, 1001, events)
        assert count == 0

    def test_multiple_owners_three_changes(self, db_session):
        events = [
            _ev("OwnerUpdate", datetime(2025, 1, 6, 10, 0, 0), new_owner="agent1"),
            _ev("OwnerUpdate", datetime(2025, 1, 6, 11, 0, 0), new_owner="agent2"),
            _ev("OwnerUpdate", datetime(2025, 1, 6, 12, 0, 0), new_owner="agent1"),
        ]
        count = ReconstructorService._build_ownership_periods(db_session, 1001, events)
        assert count == 3


class TestBuildQueuePeriods:
    def test_single_queue(self, db_session):
        events = [
            _ev("OwnerUpdate", datetime(2025, 1, 6, 10, 0, 0), queue_name="Support"),
        ]
        count = ReconstructorService._build_queue_periods(db_session, 1001, events)
        assert count == 1
        periods = db_session.query(QueuePeriod).all()
        assert periods[0].queue_name == "Support"

    def test_queue_change_via_dest_queue(self, db_session):
        events = [
            _ev("Move", datetime(2025, 1, 6, 10, 0, 0), queue_name="Support", dest_queue="Escalation"),
        ]
        count = ReconstructorService._build_queue_periods(db_session, 1001, events)
        assert count == 1
        periods = db_session.query(QueuePeriod).all()
        assert periods[0].queue_name == "Escalation"

    def test_queue_change(self, db_session):
        events = [
            _ev("OwnerUpdate", datetime(2025, 1, 6, 10, 0, 0), queue_name="Support"),
            _ev("Move", datetime(2025, 1, 6, 12, 0, 0), queue_name="Support", dest_queue="Escalation"),
        ]
        count = ReconstructorService._build_queue_periods(db_session, 1001, events)
        assert count == 2
        periods = db_session.query(QueuePeriod).order_by(QueuePeriod.id).all()
        assert periods[0].queue_name == "Support"
        assert periods[1].queue_name == "Escalation"

    def test_no_queue_change(self, db_session):
        events = [
            _ev("OwnerUpdate", datetime(2025, 1, 6, 10, 0, 0), queue_name="Support"),
            _ev("OwnerUpdate", datetime(2025, 1, 6, 12, 0, 0), queue_name="Support"),
        ]
        count = ReconstructorService._build_queue_periods(db_session, 1001, events)
        assert count == 1

    def test_owner_count_tracked(self, db_session):
        events = [
            _ev("OwnerUpdate", datetime(2025, 1, 6, 10, 0, 0), queue_name="Support", owner_name="agent1"),
            _ev("OwnerUpdate", datetime(2025, 1, 6, 11, 0, 0), queue_name="Support", owner_name="agent2"),
        ]
        count = ReconstructorService._build_queue_periods(db_session, 1001, events)
        assert count == 1
        period = db_session.query(QueuePeriod).first()
        assert period.owner_count == 2

    def test_system_owner_not_counted(self, db_session):
        events = [
            _ev("OwnerUpdate", datetime(2025, 1, 6, 10, 0, 0), queue_name="Support", owner_name="root@localhost"),
        ]
        count = ReconstructorService._build_queue_periods(db_session, 1001, events)
        period = db_session.query(QueuePeriod).first()
        assert period.owner_count == 0

    def test_empty_events(self, db_session):
        count = ReconstructorService._build_queue_periods(db_session, 1001, [])
        assert count == 0


class TestBuildTicketSnapshot:
    def test_basic_snapshot(self, db_session):
        events = [
            _ev("OwnerUpdate", datetime(2025, 1, 6, 10, 0, 0)),
            _ev("OwnerUpdate", datetime(2025, 1, 6, 12, 0, 0)),
        ]
        ReconstructorService._build_ticket_snapshot(db_session, 1001, events, uuid4())
        from app.domain.models import TicketSnapshot
        snap = db_session.query(TicketSnapshot).first()
        assert snap is not None
        assert snap.ticket_id == 1001
        assert snap.title == "Test"

    def test_first_response_detected(self, db_session):
        events = [
            _ev("OwnerUpdate", datetime(2025, 1, 6, 10, 0, 0)),
            _ev("SendAnswer", datetime(2025, 1, 6, 11, 0, 0)),
            _ev("OwnerUpdate", datetime(2025, 1, 6, 12, 0, 0)),
        ]
        ReconstructorService._build_ticket_snapshot(db_session, 1001, events, uuid4())
        from app.domain.models import TicketSnapshot
        snap = db_session.query(TicketSnapshot).first()
        assert snap.first_response_at == datetime(2025, 1, 6, 11, 0, 0)

    def test_first_response_only_first(self, db_session):
        """Only the first SendAnswer should be recorded."""
        events = [
            _ev("SendAnswer", datetime(2025, 1, 6, 10, 0, 0)),
            _ev("SendAnswer", datetime(2025, 1, 6, 11, 0, 0)),
        ]
        ReconstructorService._build_ticket_snapshot(db_session, 1001, events, uuid4())
        from app.domain.models import TicketSnapshot
        snap = db_session.query(TicketSnapshot).first()
        assert snap.first_response_at == datetime(2025, 1, 6, 10, 0, 0)

    def test_resolution_detected(self, db_session):
        events = [
            _ev("OwnerUpdate", datetime(2025, 1, 6, 10, 0, 0)),
            _ev("StateUpdate", datetime(2025, 1, 6, 12, 0, 0), new_state="closed successful"),
        ]
        ReconstructorService._build_ticket_snapshot(db_session, 1001, events, uuid4())
        from app.domain.models import TicketSnapshot
        snap = db_session.query(TicketSnapshot).first()
        assert snap.resolution_at == datetime(2025, 1, 6, 12, 0, 0)
        assert snap.is_closed is True

    def test_merged_detected(self, db_session):
        events = [
            _ev("OwnerUpdate", datetime(2025, 1, 6, 10, 0, 0)),
            _ev("Merged", datetime(2025, 1, 6, 12, 0, 0)),
        ]
        ReconstructorService._build_ticket_snapshot(db_session, 1001, events, uuid4())
        from app.domain.models import TicketSnapshot
        snap = db_session.query(TicketSnapshot).first()
        assert snap.is_merged is True

    def test_last_event_is_current_state(self, db_session):
        events = [
            _ev("OwnerUpdate", datetime(2025, 1, 6, 10, 0, 0), queue_name="Support", state_name="open"),
            _ev("OwnerUpdate", datetime(2025, 1, 6, 12, 0, 0), queue_name="Escalation", state_name="closed successful"),
        ]
        ReconstructorService._build_ticket_snapshot(db_session, 1001, events, uuid4())
        from app.domain.models import TicketSnapshot
        snap = db_session.query(TicketSnapshot).first()
        assert snap.current_queue == "Escalation"
        assert snap.current_state == "closed successful"
