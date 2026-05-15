"""Tests for CSV parsing and raw event normalization."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.core.database import sync_session_factory
from app.domain.models import ImportSession, RawEvent

pytestmark = pytest.mark.asyncio


@pytest.fixture
def db():
    session = sync_session_factory()
    yield session
    session.rollback()
    session.close()


def test_import_session_model_create(db):
    imp = ImportSession(status="draft")
    db.add(imp)
    db.flush()
    assert imp.id is not None
    assert imp.status == "draft"
    assert imp.created_at is not None


def test_import_session_status_transitions(db):
    imp = ImportSession(status="draft")
    db.add(imp)
    db.flush()
    assert imp.status == "draft"

    imp.status = "processing"
    db.flush()
    assert imp.status == "processing"

    imp.status = "completed"
    imp.completed_at = datetime.now(timezone.utc)
    db.flush()
    assert imp.completed_at is not None


def test_import_session_defaults(db):
    imp = ImportSession()
    db.add(imp)
    db.flush()
    assert imp.status == "draft"
    assert imp.stats == {}
    assert imp.error_details == []


def test_raw_event_model(db):
    import_id = uuid4()
    imp = ImportSession(id=import_id, status="draft")
    db.add(imp)
    db.flush()

    event = RawEvent(
        import_id=import_id,
        ticket_id=1001,
        ticket_number="20250101-1001",
        title="Test ticket",
        event_time="2025-01-15 10:00:00",
        event_name="OwnerUpdate",
        queue_name="Support",
        state_name="open",
    )
    db.add(event)
    db.flush()
    assert event.id is not None
    assert event.ticket_id == 1001


def test_raw_event_duplicate_key(db):
    import_id = uuid4()
    imp = ImportSession(id=import_id, status="draft")
    db.add(imp)
    db.flush()

    e1 = RawEvent(
        import_id=import_id,
        ticket_id=1001,
        event_time="2025-01-15 10:00:00",
        event_name="OwnerUpdate",
        duplicate_key="1001-abc",
    )
    e2 = RawEvent(
        import_id=import_id,
        ticket_id=1001,
        event_time="2025-01-15 10:00:00",
        event_name="OwnerUpdate",
        duplicate_key="1001-abc",
    )
    db.add(e1)
    db.add(e2)
    db.flush()
    assert e1.id != e2.id
    assert e1.duplicate_key == e2.duplicate_key


def test_import_error_details(db):
    import_id = uuid4()
    imp = ImportSession(id=import_id, status="draft")
    db.add(imp)
    db.flush()

    imp.error_details = [{"step": "parsing", "error": "Invalid CSV format"}]
    db.flush()
    assert len(imp.error_details) == 1
    assert imp.error_details[0]["step"] == "parsing"
