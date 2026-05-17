"""Unit tests for sla_engine.py — the orchestrator.

Tests the compute_for_import method with in-memory SQLite.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.models import Base, SLADefinition, SLAMetric, TicketSnapshot
from app.services.sla_engine import SLAEngine


@pytest.fixture
def db_session():
    engine = create_engine("sqlite://", echo=False)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_compute_for_import_no_tickets(db_session):
    imp_id = uuid4().hex
    result = SLAEngine.compute_for_import(db_session, imp_id)
    assert result["metrics_written"] == 0
    assert result["errors"] == []


def test_compute_for_import_no_sla_definitions(db_session):
    imp_id = uuid4().hex
    db_session.add(TicketSnapshot(
        ticket_id=1001, ticket_number="T-1001", title="Test",
        created_at=datetime(2025, 1, 6, 10, 0, 0),
        updated_at=datetime(2025, 1, 6, 12, 0, 0),
        current_queue="Support", current_state="open",
        current_owner="agent", first_response_at=datetime(2025, 1, 6, 11, 0, 0),
        resolution_at=datetime(2025, 1, 7, 10, 0, 0),
        is_closed=False, is_merged=False, confidence="full",
        last_import_id=imp_id, updated_at_ts=datetime.now(),
    ))
    db_session.commit()
    result = SLAEngine.compute_for_import(db_session, imp_id)
    assert result["metrics_written"] >= 2
    assert result["errors"] == []


def test_compute_for_import_with_sla(db_session):
    imp_id = uuid4().hex
    sla = SLADefinition(
        id=1, name="Critical", queue_pattern="*", priority="3",
        response_target_seconds=3600, resolution_target_seconds=86400,
        is_active=True,
    )
    db_session.add(sla)
    db_session.add(TicketSnapshot(
        ticket_id=1001, ticket_number="T-1001", title="Test",
        created_at=datetime(2025, 1, 6, 10, 0, 0),
        updated_at=datetime(2025, 1, 6, 12, 0, 0),
        current_queue="Support", current_state="open",
        current_owner="agent", first_response_at=datetime(2025, 1, 6, 11, 0, 0),
        resolution_at=datetime(2025, 1, 7, 10, 0, 0),
        is_closed=False, is_merged=False, confidence="full",
        last_import_id=imp_id, updated_at_ts=datetime.now(),
    ))
    db_session.commit()
    result = SLAEngine.compute_for_import(db_session, imp_id)
    assert result["metrics_written"] >= 2
    assert result["errors"] == []


def test_compute_for_import_clears_existing_metrics(db_session):
    imp_id = uuid4().hex
    db_session.add(SLAMetric(ticket_id=1001, metric_name="response_time", import_id=imp_id))
    db_session.commit()
    result = SLAEngine.compute_for_import(db_session, imp_id)
    remaining = db_session.query(SLAMetric).filter(SLAMetric.import_id == imp_id).count()
    assert remaining == result["metrics_written"]


def test_compute_for_import_no_match_sla(db_session):
    """Ticket with queue that doesn't match any SLA gets skipped."""
    imp_id = uuid4().hex
    db_session.add(SLADefinition(
        id=1, name="Support Only", queue_pattern="Support*", priority="3",
        response_target_seconds=3600, resolution_target_seconds=86400, is_active=True,
    ))
    db_session.add(TicketSnapshot(
        ticket_id=1001, ticket_number="T-1001", title="Test",
        created_at=datetime(2025, 1, 6, 10, 0, 0),
        updated_at=datetime(2025, 1, 6, 12, 0, 0),
        current_queue="Billing", current_state="open",
        current_owner="agent", confidence="full",
        last_import_id=imp_id, updated_at_ts=datetime.now(),
    ))
    db_session.commit()
    result = SLAEngine.compute_for_import(db_session, imp_id)
    assert result["metrics_written"] == 0


def test_default_sla_definition_created(db_session):
    sla = SLAEngine._default_sla_definition()
    assert sla.name == "Default Fallback"
    assert sla.queue_pattern == "*"
    assert sla.response_target_seconds == 28800
    assert sla.resolution_target_seconds == 144000
    assert sla.is_active is True
