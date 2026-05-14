import uuid
from datetime import datetime

from sqlalchemy import Boolean, BigInteger, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(200), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="viewer")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class ImportSession(Base):
    __tablename__ = "import_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String(20), nullable=False, default="draft")
    backlog_file = Column(String(500))
    history_file = Column(String(500))
    backlog_sha256 = Column(String(64))
    history_sha256 = Column(String(64))
    backlog_rows = Column(Integer)
    history_rows = Column(Integer)
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    stats = Column(JSONB, default=dict)
    error_details = Column(JSONB, default=list)
    imported_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True))


class RawEvent(Base):
    __tablename__ = "raw_events"

    id = Column(BigInteger, primary_key=True)
    import_id = Column(UUID(as_uuid=True), ForeignKey("import_sessions.id", ondelete="CASCADE"), nullable=False)
    ticket_id = Column(BigInteger, nullable=False)
    ticket_number = Column(String(20))
    title = Column(Text)
    event_time = Column(DateTime, nullable=False)
    event_name = Column(String(50), nullable=False)
    event_raw_name = Column(Text)
    queue_name = Column(String(200))
    state_name = Column(String(50))
    event_owner_name = Column(String(100))
    src_queue = Column(String(200))
    dest_queue = Column(String(200))
    old_state = Column(String(50))
    new_state = Column(String(50))
    new_owner = Column(String(100))
    pending_until = Column(DateTime)
    sla_name = Column(String(200))
    duplicate_key = Column(String(500))
    is_duplicate = Column(Boolean, default=False)


class TicketEvent(Base):
    __tablename__ = "ticket_events"

    id = Column(BigInteger, primary_key=True)
    ticket_id = Column(BigInteger, nullable=False)
    ticket_number = Column(String(20))
    event_seq = Column(Integer, nullable=False)
    event_time = Column(DateTime, nullable=False)
    event_type = Column(String(50), nullable=False)
    queue_name = Column(String(200))
    state_name = Column(String(50))
    owner_name = Column(String(100))
    src_queue = Column(String(200))
    dest_queue = Column(String(200))
    old_state = Column(String(50))
    new_state = Column(String(50))
    new_owner = Column(String(100))
    old_owner = Column(String(100))
    pending_until = Column(DateTime)
    is_system_action = Column(Boolean, default=False)
    import_id = Column(UUID(as_uuid=True), ForeignKey("import_sessions.id"))
    raw_event_id = Column(BigInteger, ForeignKey("raw_events.id"))


class TicketSnapshot(Base):
    __tablename__ = "ticket_snapshots"

    ticket_id = Column(BigInteger, primary_key=True)
    ticket_number = Column(String(20))
    title = Column(Text)
    customer_id = Column(String(200))
    customer_user_id = Column(String(200))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    current_queue = Column(String(200))
    current_state = Column(String(50))
    current_owner = Column(String(100))
    first_response_at = Column(DateTime)
    resolution_at = Column(DateTime)
    is_closed = Column(Boolean, default=False)
    is_merged = Column(Boolean, default=False)
    confidence = Column(String(20), default="partial")
    last_import_id = Column(UUID(as_uuid=True), ForeignKey("import_sessions.id"))
    updated_at_ts = Column(DateTime(timezone=True), default=datetime.utcnow)


class OwnershipPeriod(Base):
    __tablename__ = "ownership_periods"

    id = Column(BigInteger, primary_key=True)
    ticket_id = Column(BigInteger, ForeignKey("ticket_snapshots.ticket_id"), nullable=False)
    owner = Column(String(100))
    queue_name = Column(String(200))
    team_prefix = Column(String(50))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration_seconds = Column(Integer)
    is_active = Column(Boolean, default=False)


class QueuePeriod(Base):
    __tablename__ = "queue_periods"

    id = Column(BigInteger, primary_key=True)
    ticket_id = Column(BigInteger, ForeignKey("ticket_snapshots.ticket_id"), nullable=False)
    queue_name = Column(String(200), nullable=False)
    team_prefix = Column(String(50))
    entered_at = Column(DateTime, nullable=False)
    exited_at = Column(DateTime)
    duration_seconds = Column(Integer)
    owner_count = Column(Integer, default=0)


class SLADefinition(Base):
    __tablename__ = "sla_definitions"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    queue_pattern = Column(String(200))
    priority = Column(String(50))
    response_target_seconds = Column(Integer, nullable=False)
    resolution_target_seconds = Column(Integer, nullable=False)
    pause_on_pending = Column(Boolean, default=True)
    business_hours_only = Column(Boolean, default=False)
    business_hours = Column(JSONB, default=dict)
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class SLAMetric(Base):
    __tablename__ = "sla_metrics"

    id = Column(BigInteger, primary_key=True)
    ticket_id = Column(BigInteger, nullable=False)
    metric_name = Column(String(50), nullable=False)
    metric_seconds = Column(Integer)
    sla_breached = Column(Boolean)
    queue_name = Column(String(200))
    owner = Column(String(100))
    team_prefix = Column(String(50))
    sla_definition_id = Column(Integer, ForeignKey("sla_definitions.id"))
    import_id = Column(UUID(as_uuid=True), ForeignKey("import_sessions.id"))
    confidence = Column(String(20))
    computed_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    queue_prefix = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(BigInteger, primary_key=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    action = Column(String(50), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(String(100))
    details = Column(JSONB, default=dict)
    ip_address = Column(INET)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class UserTeam(Base):
    __tablename__ = "user_teams"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True)
