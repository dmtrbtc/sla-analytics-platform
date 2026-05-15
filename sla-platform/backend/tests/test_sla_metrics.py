"""Tests for SLA metric computation and pause engine."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.database import sync_session_factory
from app.domain.models import (
    ImportSession,
    SLADefinition,
    SLAMetric,
    TicketSnapshot,
)
from app.services.sla.business_hours import (
    calculate_business_seconds,
    is_business_time,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
def db():
    session = sync_session_factory()
    yield session
    session.rollback()
    session.close()


def test_sla_definition_create(db):
    sd = SLADefinition(
        name="Critical Response",
        queue_pattern="Support*",
        priority="critical",
        response_target_seconds=3600,
        resolution_target_seconds=86400,
    )
    db.add(sd)
    db.flush()
    assert sd.id is not None
    assert sd.name == "Critical Response"
    assert sd.is_active is True


def test_sla_definition_defaults(db):
    sd = SLADefinition(
        name="Default SLA",
        queue_pattern="*",
        response_target_seconds=7200,
        resolution_target_seconds=172800,
    )
    db.add(sd)
    db.flush()
    assert sd.queue_pattern == "*"
    assert sd.pause_on_pending is True
    assert sd.business_hours_only is False


def test_sla_metric_model(db):
    import_id = uuid4()
    imp = ImportSession(id=import_id, status="completed")
    db.add(imp)
    db.flush()

    ticket = TicketSnapshot(ticket_id=1001, ticket_number="T-1001")
    db.add(ticket)
    db.flush()

    metric = SLAMetric(
        ticket_id=1001,
        metric_name="response_time",
        metric_seconds=1800,
        sla_breached=False,
        import_id=import_id,
    )
    db.add(metric)
    db.flush()
    assert metric.id is not None
    assert metric.metric_seconds == 1800
    assert metric.sla_breached is False


def test_sla_metric_breached(db):
    import_id = uuid4()
    imp = ImportSession(id=import_id, status="completed")
    db.add(imp)
    db.flush()

    metric = SLAMetric(
        ticket_id=1002,
        metric_name="resolution_time",
        metric_seconds=90000,
        sla_breached=True,
        import_id=import_id,
    )
    db.add(metric)
    db.flush()
    assert metric.sla_breached is True


def test_business_hours_default_schedule():
    """Mon-Fri 09:00-18:00 by default."""
    monday_10am = datetime(2025, 1, 6, 10, 0, 0)  # Monday
    assert is_business_time(monday_10am) is True

    monday_8am = datetime(2025, 1, 6, 8, 0, 0)
    assert is_business_time(monday_8am) is False

    monday_7pm = datetime(2025, 1, 6, 19, 0, 0)
    assert is_business_time(monday_7pm) is False

    saturday = datetime(2025, 1, 11, 12, 0, 0)  # Saturday
    assert is_business_time(saturday) is False

    sunday = datetime(2025, 1, 12, 12, 0, 0)  # Sunday
    assert is_business_time(sunday) is False


def test_business_hours_24_7():
    config = {"24_7": True}
    saturday = datetime(2025, 1, 11, 12, 0, 0)
    assert is_business_time(saturday, config) is True

    midnight = datetime(2025, 1, 11, 0, 0, 0)
    assert is_business_time(midnight, config) is True


def test_calculate_business_seconds_same_day():
    start = datetime(2025, 1, 6, 10, 0, 0)  # Monday 10am
    end = datetime(2025, 1, 6, 12, 0, 0)  # Monday 12pm
    result = calculate_business_seconds(start, end)
    assert result == 7200  # 2 hours


def test_calculate_business_seconds_overnight():
    start = datetime(2025, 1, 6, 17, 0, 0)  # Monday 5pm
    end = datetime(2025, 1, 7, 10, 0, 0)  # Tuesday 10am
    result = calculate_business_seconds(start, end)
    # Monday: 1 hour (5pm-6pm), Tuesday: 1 hour (9am-10am) = 7200
    assert result == 7200


def test_calculate_business_seconds_weekend():
    start = datetime(2025, 1, 10, 17, 0, 0)  # Friday 5pm
    end = datetime(2025, 1, 13, 10, 0, 0)  # Monday 10am
    result = calculate_business_seconds(start, end)
    # Friday: 1 hour (5pm-6pm), Monday: 1 hour (9am-10am) = 7200
    assert result == 7200


def test_calculate_business_seconds_24_7():
    config = {"24_7": True}
    start = datetime(2025, 1, 11, 10, 0, 0)  # Saturday 10am
    end = datetime(2025, 1, 11, 14, 0, 0)  # Saturday 2pm
    result = calculate_business_seconds(start, end, config)
    assert result == 14400  # 4 hours


from uuid import uuid4 as _uuid4
