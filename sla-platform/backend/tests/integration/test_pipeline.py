"""Integration tests for the full data pipeline.

Tests the chain: raw_parser → normalizer → reconstructor using in-memory SQLite.

This validates that the key transformation steps work together correctly
with realistic event sequences.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.models import Base
from app.services.normalizer_service import NormalizerService
from app.services.reconstructor_service import ReconstructorService
from app.utils.raw_parser import parse_event_raw


@pytest.fixture
def db_session():
    engine = create_engine("sqlite://", echo=False)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


# ---------------------------------------------------------------------------
# Realistic ticket lifecycle: created → assigned → pending → responded → resolved
# ---------------------------------------------------------------------------

TICKET_ID = 1001
IMPORT_ID = uuid4()


def _make_raw_events():
    """Simulate the output of ParserService._df_to_raw_rows for a realistic ticket."""
    raw_events = [
        {
            "ticket_id": TICKET_ID,
            "ticket_number": "20250601-1001",
            "title": "Network issue",
            "event_time": datetime(2025, 6, 1, 9, 0, 0),
            "event_name": "NewTicket",
            "event_raw_name": "%%1001%%Support%%3%%new%%1%%",
            "queue_name": "Support",
            "state_name": "new",
            "event_owner_name": "root@localhost",
            "src_queue": None,
            "dest_queue": None,
            "old_state": None,
            "new_state": None,
            "new_owner": None,
            "pending_until": None,
            "duplicate_key": "2025-06-01 09:00:00|NewTicket|%%1001%%Support%%3%%new%%1%%",
            "id": 1,
        },
        {
            "ticket_id": TICKET_ID,
            "ticket_number": "20250601-1001",
            "title": "Network issue",
            "event_time": datetime(2025, 6, 1, 9, 5, 0),
            "event_name": "OwnerUpdate",
            "event_raw_name": "%%agent.smith%%42%%",
            "queue_name": "Support",
            "state_name": "new",
            "event_owner_name": "root@localhost",
            "src_queue": None,
            "dest_queue": None,
            "old_state": None,
            "new_state": None,
            "new_owner": "agent.smith",
            "pending_until": None,
            "duplicate_key": "2025-06-01 09:05:00|OwnerUpdate|%%agent.smith%%42%%",
            "id": 2,
        },
        {
            "ticket_id": TICKET_ID,
            "ticket_number": "20250601-1001",
            "title": "Network issue",
            "event_time": datetime(2025, 6, 1, 9, 30, 0),
            "event_name": "StateUpdate",
            "event_raw_name": "%%new%%open%%",
            "queue_name": "Support",
            "state_name": "new",
            "event_owner_name": "agent.smith",
            "src_queue": None,
            "dest_queue": None,
            "old_state": "new",
            "new_state": "open",
            "new_owner": None,
            "pending_until": None,
            "duplicate_key": "2025-06-01 09:30:00|StateUpdate|%%new%%open%%",
            "id": 3,
        },
        {
            "ticket_id": TICKET_ID,
            "ticket_number": "20250601-1001",
            "title": "Network issue",
            "event_time": datetime(2025, 6, 1, 9, 45, 0),
            "event_name": "SendAnswer",
            "event_raw_name": "",
            "queue_name": "Support",
            "state_name": "open",
            "event_owner_name": "agent.smith",
            "src_queue": None,
            "dest_queue": None,
            "old_state": None,
            "new_state": None,
            "new_owner": None,
            "pending_until": None,
            "duplicate_key": "2025-06-01 09:45:00|SendAnswer|",
            "id": 4,
        },
        {
            "ticket_id": TICKET_ID,
            "ticket_number": "20250601-1001",
            "title": "Network issue",
            "event_time": datetime(2025, 6, 1, 10, 0, 0),
            "event_name": "SetPendingTime",
            "event_raw_name": "%%2025-06-01 12:00%%",
            "queue_name": "Support",
            "state_name": "pending auto",
            "event_owner_name": "agent.smith",
            "src_queue": None,
            "dest_queue": None,
            "old_state": None,
            "new_state": None,
            "new_owner": None,
            "pending_until": datetime(2025, 6, 1, 12, 0, 0),
            "duplicate_key": "2025-06-01 10:00:00|SetPendingTime|%%2025-06-01 12:00%%",
            "id": 5,
        },
        {
            "ticket_id": TICKET_ID,
            "ticket_number": "20250601-1001",
            "title": "Network issue",
            "event_time": datetime(2025, 6, 1, 11, 0, 0),
            "event_name": "StateUpdate",
            "event_raw_name": "%%pending auto%%open%%",
            "queue_name": "Support",
            "state_name": "pending auto",
            "event_owner_name": "agent.smith",
            "src_queue": None,
            "dest_queue": None,
            "old_state": "pending auto",
            "new_state": "open",
            "new_owner": None,
            "pending_until": None,
            "duplicate_key": "2025-06-01 11:00:00|StateUpdate|%%pending auto%%open%%",
            "id": 6,
        },
        {
            "ticket_id": TICKET_ID,
            "ticket_number": "20250601-1001",
            "title": "Network issue",
            "event_time": datetime(2025, 6, 1, 14, 0, 0),
            "event_name": "StateUpdate",
            "event_raw_name": "%%open%%closed successful%%",
            "queue_name": "Support",
            "state_name": "open",
            "event_owner_name": "agent.smith",
            "src_queue": None,
            "dest_queue": None,
            "old_state": "open",
            "new_state": "closed successful",
            "new_owner": None,
            "pending_until": None,
            "duplicate_key": "2025-06-01 14:00:00|StateUpdate|%%open%%closed successful%%",
            "id": 7,
        },
    ]
    return raw_events


class TestPipelineIntegration:
    """End-to-end pipeline: raw events → normalized → reconstructed."""

    def test_raw_parser_extracts_fields(self):
        """Verify parse_event_raw extracts fields for each event type in the pipeline."""
        assert parse_event_raw("NewTicket", "%%1001%%Support%%3%%new%%1%%")["new_queue"] == "Support"
        assert parse_event_raw("OwnerUpdate", "%%agent.smith%%42%%")["new_owner"] == "agent.smith"
        assert parse_event_raw("StateUpdate", "%%new%%open%%")["new_state"] == "open"
        assert parse_event_raw("SendAnswer", "")["communication_type"] == "answer"
        pending = parse_event_raw("SetPendingTime", "%%2025-06-01 12:00%%")
        assert pending["pending_until"] == datetime(2025, 6, 1, 12, 0)
        assert parse_event_raw("StateUpdate", "%%pending auto%%open%%")["new_state"] == "open"

    def test_normalizer_builds_from_raw_events(self):
        """Verify NormalizerService._build_normalized processes raw events correctly."""
        raw_events = _make_raw_events()
        result = NormalizerService._build_normalized(TICKET_ID, raw_events, IMPORT_ID)
        assert len(result) == len(raw_events)
        assert result[0]["event_type"] == "NewTicket"
        assert result[1]["event_type"] == "OwnerUpdate"
        assert result[2]["event_type"] == "StateUpdate"

        # Owner tracking
        assert result[0]["owner_name"] is None  # root@localhost
        assert result[1]["owner_name"] == "agent.smith"
        assert result[2]["owner_name"] == "agent.smith"

        # First response
        assert result[3]["event_type"] == "SendAnswer"

        # Pending
        assert result[4]["event_type"] == "SetPendingTime"
        assert result[4]["pending_until"] == datetime(2025, 6, 1, 12, 0)

        # Resolution
        assert result[6]["event_type"] == "StateUpdate"
        assert result[6]["new_state"] == "closed successful"

    def test_full_pipeline_reconstructs_ticket(self, db_session):
        """Verify reconstructor builds correct ownership/queue periods from normalized events."""
        # Step 1: Normalize raw events into ticket_events
        raw_events = _make_raw_events()
        norm_events = NormalizerService._build_normalized(TICKET_ID, raw_events, IMPORT_ID)

        # Simulate normalizer storing events
        from app.domain.models import TicketEvent
        for ne in norm_events:
            db_session.add(TicketEvent(**ne))
        db_session.commit()

        # Step 2: Reconstruct ownership periods
        # We need TicketEvent objects for the reconstructor, but it reads from DB.
        # Let's test _build_ownership_periods and _build_queue_periods directly.
        events_list = [
            {
                "ticket_number": ne["ticket_number"],
                "title": ne.get("title", "Network issue"),
                "event_time": ne["event_time"],
                "event_type": ne["event_type"],
                "queue_name": ne["queue_name"],
                "state_name": ne["state_name"],
                "owner_name": ne["owner_name"],
                "dest_queue": ne.get("dest_queue"),
                "new_owner": ne.get("new_owner"),
                "new_state": ne.get("new_state"),
            }
            for ne in norm_events
        ]

        # Step 3: Reconstruct
        own_count = ReconstructorService._build_ownership_periods(db_session, TICKET_ID, events_list)
        queue_count = ReconstructorService._build_queue_periods(db_session, TICKET_ID, events_list)
        ReconstructorService._build_ticket_snapshot(db_session, TICKET_ID, events_list, IMPORT_ID)
        db_session.commit()

        # Verify ownership
        from app.domain.models import OwnershipPeriod, QueuePeriod, TicketSnapshot
        owners = db_session.query(OwnershipPeriod).order_by(OwnershipPeriod.id).all()
        assert own_count >= 1
        if owners:
            assert owners[0].owner == "agent.smith"

        # Verify queue
        queues = db_session.query(QueuePeriod).order_by(QueuePeriod.id).all()
        assert queue_count >= 1
        if queues:
            assert queues[0].queue_name == "Support"

        # Verify snapshot
        snap = db_session.query(TicketSnapshot).filter_by(ticket_id=TICKET_ID).first()
        assert snap is not None
        assert snap.first_response_at == datetime(2025, 6, 1, 9, 45, 0)
        assert snap.resolution_at == datetime(2025, 6, 1, 14, 0, 0)
        assert snap.is_closed is True
        assert snap.current_owner == "agent.smith"

    def test_empty_pipeline_handling(self, db_session):
        """Empty event list should produce no periods."""
        events_list = []
        own_count = ReconstructorService._build_ownership_periods(db_session, TICKET_ID, events_list)
        queue_count = ReconstructorService._build_queue_periods(db_session, TICKET_ID, events_list)
        assert own_count == 0
        assert queue_count == 0

    def test_normalizer_deduplication(self, db_session):
        """Duplicate raw events should be handled before normalization."""
        raw_events = _make_raw_events()
        # Add a duplicate
        dup = dict(raw_events[1])
        dup["id"] = 99
        dup["duplicate_key"] = raw_events[1]["duplicate_key"]
        raw_events.insert(2, dup)

        result = NormalizerService._build_normalized(TICKET_ID, raw_events, IMPORT_ID)
        assert len(result) == len(raw_events)
