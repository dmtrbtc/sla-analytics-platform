"""Factory boy fixtures for test models."""

from datetime import datetime, timezone
from uuid import uuid4

import factory
from factory.fuzzy import FuzzyChoice, FuzzyDateTime, FuzzyInteger, FuzzyText

from app.domain.models import (
    ImportSession,
    RawEvent,
    SLADefinition,
    SLAMetric,
    TicketEvent,
    TicketSnapshot,
    Team,
    User,
)


class UserFactory(factory.Factory):
    class Meta:
        model = User

    id = factory.LazyFunction(uuid4)
    email = factory.Sequence(lambda n: f"user{n}@test.dev")
    display_name = FuzzyText()
    password_hash = "$2b$12$dummyhash"
    role = FuzzyChoice(["admin", "viewer", "analyst"])
    is_active = True
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


class ImportSessionFactory(factory.Factory):
    class Meta:
        model = ImportSession

    id = factory.LazyFunction(uuid4)
    status = FuzzyChoice(["draft", "processing", "completed", "failed"])
    stats = {}
    error_details = []
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


class RawEventFactory(factory.Factory):
    class Meta:
        model = RawEvent

    id = factory.Sequence(lambda n: n + 1)
    import_id = factory.LazyFunction(uuid4)
    ticket_id = FuzzyInteger(1000, 9999)
    ticket_number = factory.Sequence(lambda n: f"20250101-{n+1000}")
    title = FuzzyText()
    event_time = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    event_name = "OwnerUpdate"
    event_raw_name = "%%agent1%%42%%"
    queue_name = "Support"
    state_name = "open"
    event_owner_name = "agent@test.dev"
    src_queue = None
    dest_queue = None
    old_state = None
    new_state = None
    new_owner = None
    pending_until = None
    sla_name = None
    duplicate_key = factory.Sequence(lambda n: f"2025-01-01 10:00:00|OwnerUpdate|%%agent{n}%%42%%")


class TicketEventFactory(factory.Factory):
    class Meta:
        model = TicketEvent

    id = factory.Sequence(lambda n: n + 1)
    ticket_id = FuzzyInteger(1000, 9999)
    ticket_number = factory.Sequence(lambda n: f"20250101-{n+1000}")
    event_seq = factory.Sequence(lambda n: n + 1)
    event_time = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    event_type = "OwnerUpdate"
    queue_name = "Support"
    state_name = "open"
    owner_name = "agent@test.dev"
    src_queue = None
    dest_queue = None
    old_state = None
    new_state = None
    new_owner = None
    old_owner = None
    pending_until = None
    is_system_action = False
    import_id = factory.LazyFunction(uuid4)
    raw_event_id = factory.Sequence(lambda n: n + 1)


class TicketSnapshotFactory(factory.Factory):
    class Meta:
        model = TicketSnapshot

    ticket_id = factory.Sequence(lambda n: n + 1000)
    ticket_number = factory.Sequence(lambda n: f"T-{n+1000}")
    title = FuzzyText()
    customer_id = None
    customer_user_id = None
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    current_queue = "Support"
    current_state = "open"
    current_owner = "agent@test.dev"
    first_response_at = None
    resolution_at = None
    is_closed = False
    is_merged = False
    confidence = "partial"
    last_import_id = factory.LazyFunction(uuid4)
    updated_at_ts = factory.LazyFunction(lambda: datetime.now(timezone.utc))


class SLADefinitionFactory(factory.Factory):
    class Meta:
        model = SLADefinition

    id = factory.Sequence(lambda n: n + 1)
    name = FuzzyText()
    queue_pattern = "*"
    priority = None
    response_target_seconds = 3600
    resolution_target_seconds = 86400
    pause_on_pending = True
    business_hours_only = False
    business_hours = None
    is_active = True
    created_by = None
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


class SLAMetricFactory(factory.Factory):
    class Meta:
        model = SLAMetric

    id = factory.Sequence(lambda n: n + 1)
    ticket_id = FuzzyInteger(1000, 9999)
    metric_name = "response_time"
    metric_seconds = FuzzyInteger(100, 10000)
    sla_breached = False
    queue_name = "Support"
    owner = "agent@test.dev"
    team_prefix = "Su"
    sla_definition_id = 1
    import_id = factory.LazyFunction(uuid4)
    confidence = "partial"
    computed_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


class TeamFactory(factory.Factory):
    class Meta:
        model = Team

    id = factory.Sequence(lambda n: n + 1)
    name = FuzzyText()
    queue_prefix = FuzzyChoice(["Su", "IT", "HR", "BI"])
    description = None
    is_active = True
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
