"""Unit tests for metrics_engine.py — response, resolution, queue, and owner time computation.

Uses in-memory SQLite for fast test DB.
"""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.models import (
    Base,
    QueuePeriod,
    OwnershipPeriod,
    SLAQueueRule,
    TicketSnapshot,
    SLADefinition,
)
from app.services.sla.metrics_engine import MetricsEngine


@pytest.fixture
def db_session():
    engine = create_engine("sqlite://", echo=False)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def _sla(**kw) -> SLADefinition:
    defaults = dict(
        id=1, name="Test SLA", queue_pattern="*", priority="3",
        response_target_seconds=3600, resolution_target_seconds=86400,
        pause_on_pending=True, business_hours_only=False,
        business_hours=None, is_active=True,
    )
    defaults.update(kw)
    return SLADefinition(**defaults)


def _ticket(**kw) -> TicketSnapshot:
    defaults = dict(
        ticket_id=1001, ticket_number="T-1001", title="Test",
        created_at=datetime(2025, 1, 6, 10, 0, 0),
        updated_at=datetime(2025, 1, 6, 12, 0, 0),
        current_queue="Support", current_state="open",
        current_owner="agent@test.dev",
        first_response_at=None, resolution_at=None,
        is_closed=False, is_merged=False, confidence="full",
        last_import_id=uuid4(), updated_at_ts=datetime.now(),
    )
    defaults.update(kw)
    return TicketSnapshot(**defaults)


def _queue_rule(**kw) -> SLAQueueRule:
    defaults = dict(
        id=None,
        name="Test Queue Rule",
        queue_pattern="Support*",
        priority=10,
        response_target_seconds=1800,
        resolution_target_seconds=43200,
        is_active=True,
        description=None,
    )
    defaults.update(kw)
    return SLAQueueRule(**defaults)


class TestResolveQueueRule:
    def test_no_queue_name(self, db_session):
        result = MetricsEngine.resolve_sla_rule_by_queue(db_session, None)
        assert result is None

    def test_no_rules(self, db_session):
        result = MetricsEngine.resolve_sla_rule_by_queue(db_session, "Support")
        assert result is None

    def test_wildcard_match(self, db_session):
        db_session.add(_queue_rule(queue_pattern="*", priority=0))
        db_session.commit()
        result = MetricsEngine.resolve_sla_rule_by_queue(db_session, "AnyQueue")
        assert result is not None
        assert result.queue_pattern == "*"

    def test_specific_match(self, db_session):
        db_session.add(_queue_rule(queue_pattern="Support*", priority=10))
        db_session.commit()
        result = MetricsEngine.resolve_sla_rule_by_queue(db_session, "Support::IT")
        assert result is not None
        assert result.queue_pattern == "Support*"

    def test_no_match(self, db_session):
        db_session.add(_queue_rule(queue_pattern="Escalation*", priority=10))
        db_session.commit()
        result = MetricsEngine.resolve_sla_rule_by_queue(db_session, "Support")
        assert result is None

    def test_priority_order(self, db_session):
        db_session.add_all([
            _queue_rule(queue_pattern="Support*", priority=5, name="Low"),
            _queue_rule(queue_pattern="Support*", priority=20, name="High"),
        ])
        db_session.commit()
        result = MetricsEngine.resolve_sla_rule_by_queue(db_session, "Support::IT")
        assert result is not None
        assert result.name == "High"

    def test_inactive_skipped(self, db_session):
        db_session.add(_queue_rule(queue_pattern="Support*", priority=10, is_active=False))
        db_session.commit()
        result = MetricsEngine.resolve_sla_rule_by_queue(db_session, "Support::IT")
        assert result is None


class TestComputeResponseTime:
    def test_no_created_at(self, db_session):
        ticket = _ticket(created_at=None, first_response_at=datetime(2025, 1, 6, 11, 0, 0))
        result = MetricsEngine.compute_response_time(db_session, ticket, _sla(), uuid4().hex)
        assert result is None

    def test_no_first_response(self, db_session):
        ticket = _ticket(created_at=datetime(2025, 1, 6, 10, 0, 0), first_response_at=None)
        result = MetricsEngine.compute_response_time(db_session, ticket, _sla(), uuid4().hex)
        assert result is None

    def test_metric_computed(self, db_session):
        ticket = _ticket(
            created_at=datetime(2025, 1, 6, 10, 0, 0),
            first_response_at=datetime(2025, 1, 6, 11, 0, 0),
        )
        result = MetricsEngine.compute_response_time(db_session, ticket, _sla(), uuid4().hex)
        assert result is not None
        assert result.metric_name == "response_time"
        assert result.metric_seconds == 3600
        assert result.sla_breached is False

    def test_breached(self, db_session):
        ticket = _ticket(
            created_at=datetime(2025, 1, 6, 10, 0, 0),
            first_response_at=datetime(2025, 1, 6, 15, 0, 0),
        )
        sla = _sla(response_target_seconds=3600)
        result = MetricsEngine.compute_response_time(db_session, ticket, sla, uuid4().hex)
        assert result is not None
        assert result.sla_breached is True

    def test_no_target_no_breach(self, db_session):
        ticket = _ticket(
            created_at=datetime(2025, 1, 6, 10, 0, 0),
            first_response_at=datetime(2025, 1, 6, 15, 0, 0),
        )
        sla = _sla(response_target_seconds=0)
        result = MetricsEngine.compute_response_time(db_session, ticket, sla, uuid4().hex)
        assert result is not None
        assert result.sla_breached is False


class TestComputeResponseTimeWithQueueRule:
    def test_queue_rule_override_target(self, db_session):
        db_session.add(_queue_rule(
            queue_pattern="Support*", priority=10,
            response_target_seconds=600,  # 10 min
        ))
        db_session.commit()
        ticket = _ticket(
            current_queue="Support::IT",
            created_at=datetime(2025, 1, 6, 10, 0, 0),
            first_response_at=datetime(2025, 1, 6, 10, 20, 0),  # 20 min > 10 min
        )
        sla = _sla(response_target_seconds=3600)  # would NOT breach with this
        result = MetricsEngine.compute_response_time(db_session, ticket, sla, uuid4().hex)
        assert result is not None
        assert result.sla_breached is True  # breached because queue rule is stricter

    def test_queue_rule_no_override_if_no_match(self, db_session):
        db_session.add(_queue_rule(
            queue_pattern="Escalation*", priority=10,
            response_target_seconds=600,
        ))
        db_session.commit()
        ticket = _ticket(
            current_queue="Support::IT",
            created_at=datetime(2025, 1, 6, 10, 0, 0),
            first_response_at=datetime(2025, 1, 6, 10, 20, 0),
        )
        sla = _sla(response_target_seconds=3600)
        result = MetricsEngine.compute_response_time(db_session, ticket, sla, uuid4().hex)
        assert result is not None
        assert result.sla_breached is False  # uses sla_def target since no queue rule match


class TestComputeResolutionTime:
    def test_no_created_at(self, db_session):
        ticket = _ticket(created_at=None, resolution_at=datetime(2025, 1, 7, 10, 0, 0))
        result = MetricsEngine.compute_resolution_time(db_session, ticket, _sla(), uuid4().hex)
        assert result is None

    def test_no_resolution(self, db_session):
        ticket = _ticket(created_at=datetime(2025, 1, 6, 10, 0, 0), resolution_at=None)
        result = MetricsEngine.compute_resolution_time(db_session, ticket, _sla(), uuid4().hex)
        assert result is None

    def test_metric_computed(self, db_session):
        end = datetime(2025, 1, 7, 10, 0, 0)
        ticket = _ticket(created_at=datetime(2025, 1, 6, 10, 0, 0), resolution_at=end)
        sla = _sla(resolution_target_seconds=86400)
        result = MetricsEngine.compute_resolution_time(db_session, ticket, sla, uuid4().hex)
        assert result is not None
        assert result.metric_name == "resolution_time"
        assert result.metric_seconds == 86400
        assert result.sla_breached is False

    def test_breached(self, db_session):
        ticket = _ticket(
            created_at=datetime(2025, 1, 6, 10, 0, 0),
            resolution_at=datetime(2025, 1, 9, 10, 0, 0),
        )
        sla = _sla(resolution_target_seconds=86400)
        result = MetricsEngine.compute_resolution_time(db_session, ticket, sla, uuid4().hex)
        assert result is not None
        assert result.sla_breached is True


class TestComputeQueueTime:
    def test_no_queue_periods(self, db_session):
        ticket = _ticket()
        result = MetricsEngine.compute_queue_time(db_session, ticket, _sla(), uuid4().hex)
        assert result == []

    def test_single_queue(self, db_session):
        ticket = _ticket()
        imp_id = uuid4().hex
        db_session.add(QueuePeriod(
            ticket_id=1001, queue_name="Support",
            entered_at=datetime(2025, 1, 6, 10, 0, 0),
            exited_at=datetime(2025, 1, 6, 12, 0, 0),
            duration_seconds=7200, owner_count=1,
        ))
        db_session.commit()
        result = MetricsEngine.compute_queue_time(db_session, ticket, _sla(), imp_id)
        assert len(result) == 1
        assert result[0].metric_name == "queue_time"
        assert result[0].queue_name == "Support"
        assert result[0].metric_seconds == 7200

    def test_multiple_queues(self, db_session):
        ticket = _ticket()
        imp_id = uuid4().hex
        db_session.add_all([
            QueuePeriod(ticket_id=1001, queue_name="Support", entered_at=datetime(2025, 1, 6, 10, 0, 0), exited_at=datetime(2025, 1, 6, 11, 0, 0), duration_seconds=3600, owner_count=1),
            QueuePeriod(ticket_id=1001, queue_name="Escalation", entered_at=datetime(2025, 1, 6, 11, 0, 0), exited_at=datetime(2025, 1, 6, 12, 0, 0), duration_seconds=3600, owner_count=1),
        ])
        db_session.commit()
        result = MetricsEngine.compute_queue_time(db_session, ticket, _sla(), imp_id)
        assert len(result) == 2
        assert result[0].queue_name == "Support"
        assert result[1].queue_name == "Escalation"

    def test_skips_periods_without_entered_at(self, db_session):
        ticket = _ticket()
        db_session.add(QueuePeriod(ticket_id=1001, queue_name="Support", entered_at=None, exited_at=None, duration_seconds=0, owner_count=0))
        db_session.commit()
        result = MetricsEngine.compute_queue_time(db_session, ticket, _sla(), uuid4().hex)
        assert result == []


class TestComputeOwnerTime:
    def test_no_ownership_periods(self, db_session):
        ticket = _ticket()
        result = MetricsEngine.compute_owner_time(db_session, ticket, _sla(), uuid4().hex)
        assert result == []

    def test_single_owner(self, db_session):
        ticket = _ticket()
        imp_id = uuid4().hex
        db_session.add(OwnershipPeriod(
            ticket_id=1001, owner="agent@test.dev", queue_name="Support",
            start_time=datetime(2025, 1, 6, 10, 0, 0),
            end_time=datetime(2025, 1, 6, 12, 0, 0),
            duration_seconds=7200, is_active=False,
        ))
        db_session.commit()
        result = MetricsEngine.compute_owner_time(db_session, ticket, _sla(), imp_id)
        assert len(result) == 1
        assert result[0].metric_name == "owner_time"
        assert result[0].owner == "agent@test.dev"
        assert result[0].metric_seconds == 7200

    def test_multiple_owners(self, db_session):
        ticket = _ticket()
        imp_id = uuid4().hex
        db_session.add_all([
            OwnershipPeriod(ticket_id=1001, owner="agent1", queue_name="Support", start_time=datetime(2025, 1, 6, 10, 0, 0), end_time=datetime(2025, 1, 6, 11, 0, 0), duration_seconds=3600),
            OwnershipPeriod(ticket_id=1001, owner="agent2", queue_name="Support", start_time=datetime(2025, 1, 6, 11, 0, 0), end_time=datetime(2025, 1, 6, 12, 0, 0), duration_seconds=3600),
        ])
        db_session.commit()
        result = MetricsEngine.compute_owner_time(db_session, ticket, _sla(), imp_id)
        assert len(result) == 2
        assert result[0].owner == "agent1"
        assert result[1].owner == "agent2"


class TestComputeResolutionTimeWithQueueRule:
    def test_queue_rule_override_resolution(self, db_session):
        db_session.add(_queue_rule(
            queue_pattern="Support*", priority=10,
            resolution_target_seconds=14400,  # 4 hours
        ))
        db_session.commit()
        ticket = _ticket(
            current_queue="Support::IT",
            created_at=datetime(2025, 1, 6, 10, 0, 0),
            resolution_at=datetime(2025, 1, 6, 20, 0, 0),  # 10 hours > 4 hours
        )
        sla = _sla(resolution_target_seconds=86400)  # would NOT breach with this
        result = MetricsEngine.compute_resolution_time(db_session, ticket, sla, uuid4().hex)
        assert result is not None
        assert result.sla_breached is True

    def test_queue_rule_no_override_resolution(self, db_session):
        db_session.add(_queue_rule(
            queue_pattern="Escalation*", priority=10,
            resolution_target_seconds=14400,
        ))
        db_session.commit()
        ticket = _ticket(
            current_queue="Support::IT",
            created_at=datetime(2025, 1, 6, 10, 0, 0),
            resolution_at=datetime(2025, 1, 6, 20, 0, 0),
        )
        sla = _sla(resolution_target_seconds=86400)
        result = MetricsEngine.compute_resolution_time(db_session, ticket, sla, uuid4().hex)
        assert result is not None
        assert result.sla_breached is False


class TestComputeAll:
    def test_all_metrics_no_queue_or_owner(self, db_session):
        ticket = _ticket(
            first_response_at=datetime(2025, 1, 6, 11, 0, 0),
            resolution_at=datetime(2025, 1, 7, 10, 0, 0),
        )
        sla = _sla()
        result = MetricsEngine.compute_all(db_session, ticket, sla, uuid4().hex)
        assert len(result) == 2  # response + resolution
        names = {m.metric_name for m in result}
        assert names == {"response_time", "resolution_time"}

    def test_all_metrics_with_queue_and_owner(self, db_session):
        ticket = _ticket(
            first_response_at=datetime(2025, 1, 6, 11, 0, 0),
            resolution_at=datetime(2025, 1, 7, 10, 0, 0),
        )
        imp_id = uuid4().hex
        db_session.add(QueuePeriod(ticket_id=1001, queue_name="Support", entered_at=datetime(2025, 1, 6, 10, 0, 0), exited_at=datetime(2025, 1, 6, 18, 0, 0), duration_seconds=28800, owner_count=1))
        db_session.add(OwnershipPeriod(ticket_id=1001, owner="agent@test.dev", queue_name="Support", start_time=datetime(2025, 1, 6, 10, 0, 0), end_time=datetime(2025, 1, 6, 18, 0, 0), duration_seconds=28800))
        db_session.commit()
        sla = _sla()
        result = MetricsEngine.compute_all(db_session, ticket, sla, imp_id)
        names = {m.metric_name for m in result}
        assert "response_time" in names
        assert "resolution_time" in names
        assert "queue_time" in names
        assert "owner_time" in names
