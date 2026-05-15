"""Tests for audit logging."""

import pytest

from app.core.database import sync_session_factory
from app.domain.models import AuditLog
from app.services.audit_service import AuditService

pytestmark = pytest.mark.asyncio


@pytest.fixture
def db():
    session = sync_session_factory()
    yield session
    session.rollback()
    session.close()


def test_audit_log_create(db):
    log = AuditLog(
        action="test_action",
        resource_type="test",
        resource_id="123",
        details={"key": "value"},
    )
    db.add(log)
    db.flush()
    assert log.id is not None
    assert log.action == "test_action"
    assert log.details == {"key": "value"}


def test_audit_service_log(db):
    log = AuditService.log(
        db,
        action="user_login",
        actor_id=None,
        resource_type=None,
        resource_id=None,
        details={"email": "test@test.com"},
    )
    assert log.id is not None
    assert log.action == "user_login"


def test_audit_service_log_with_all_fields(db):
    log = AuditService.log(
        db,
        action="user_created",
        actor_id=None,
        resource_type="user",
        resource_id="resource-002",
        details={"role": "admin"},
        ip_address="192.168.1.1",
    )
    assert log.actor_id is None
    assert log.resource_type == "user"
    assert log.details == {"role": "admin"}


def test_audit_service_log_sync():
    AuditService.log_sync(
        action="sync_test",
        resource_type="test",
    )
    # No exception means success


def test_audit_list_logs(db):
    AuditService.log(db, action="action_a")
    AuditService.log(db, action="action_b")
    db.flush()

    logs, total = AuditService.list_logs(db, limit=10)
    assert total >= 2
    assert len(logs) >= 2


def test_audit_list_logs_filtered(db):
    AuditService.log(db, action="filter_me")
    AuditService.log(db, action="keep_me")
    db.flush()

    logs, total = AuditService.list_logs(db, limit=10, action="filter_me")
    assert total >= 1
    for log in logs:
        assert log.action == "filter_me"
