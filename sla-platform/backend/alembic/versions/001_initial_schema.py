"""Initial schema: all tables

Revision ID: 001
Revises:
Create Date: 2026-05-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "import_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("backlog_file", sa.String(500)),
        sa.Column("history_file", sa.String(500)),
        sa.Column("backlog_sha256", sa.String(64)),
        sa.Column("history_sha256", sa.String(64)),
        sa.Column("backlog_rows", sa.Integer()),
        sa.Column("history_rows", sa.Integer()),
        sa.Column("period_start", sa.DateTime()),
        sa.Column("period_end", sa.DateTime()),
        sa.Column("stats", JSONB(), server_default="{}"),
        sa.Column("error_details", JSONB(), server_default="[]"),
        sa.Column("imported_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("queue_prefix", sa.String(100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "raw_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("import_id", UUID(as_uuid=True), sa.ForeignKey("import_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("ticket_number", sa.String(20)),
        sa.Column("title", sa.Text()),
        sa.Column("event_time", sa.DateTime(), nullable=False),
        sa.Column("event_name", sa.String(50), nullable=False),
        sa.Column("event_raw_name", sa.Text()),
        sa.Column("queue_name", sa.String(200)),
        sa.Column("state_name", sa.String(50)),
        sa.Column("event_owner_name", sa.String(100)),
        sa.Column("src_queue", sa.String(200)),
        sa.Column("dest_queue", sa.String(200)),
        sa.Column("old_state", sa.String(50)),
        sa.Column("new_state", sa.String(50)),
        sa.Column("new_owner", sa.String(100)),
        sa.Column("pending_until", sa.DateTime()),
        sa.Column("sla_name", sa.String(200)),
        sa.Column("duplicate_key", sa.String(500)),
        sa.Column("is_duplicate", sa.Boolean(), server_default="false"),
    )
    op.create_index("ix_raw_events_import_id", "raw_events", ["import_id"])
    op.create_index("ix_raw_events_ticket_id", "raw_events", ["ticket_id"])
    op.create_index("ix_raw_events_import_ticket", "raw_events", ["import_id", "ticket_id"])

    op.create_table(
        "ticket_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("ticket_number", sa.String(20)),
        sa.Column("event_seq", sa.Integer(), nullable=False),
        sa.Column("event_time", sa.DateTime(), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("queue_name", sa.String(200)),
        sa.Column("state_name", sa.String(50)),
        sa.Column("owner_name", sa.String(100)),
        sa.Column("src_queue", sa.String(200)),
        sa.Column("dest_queue", sa.String(200)),
        sa.Column("old_state", sa.String(50)),
        sa.Column("new_state", sa.String(50)),
        sa.Column("new_owner", sa.String(100)),
        sa.Column("old_owner", sa.String(100)),
        sa.Column("pending_until", sa.DateTime()),
        sa.Column("is_system_action", sa.Boolean(), server_default="false"),
        sa.Column("import_id", UUID(as_uuid=True), sa.ForeignKey("import_sessions.id")),
        sa.Column("raw_event_id", sa.BigInteger(), sa.ForeignKey("raw_events.id")),
    )
    op.create_index("ix_ticket_events_ticket_id", "ticket_events", ["ticket_id"])
    op.create_index("ix_ticket_events_import_id", "ticket_events", ["import_id"])
    op.create_index("ix_ticket_events_time", "ticket_events", ["event_time"])
    op.create_index("ix_ticket_events_ticket_seq", "ticket_events", ["ticket_id", "event_seq"])
    op.create_index("ix_ticket_events_import_ticket_seq", "ticket_events", ["import_id", "ticket_id", "event_seq"], unique=True)

    op.create_table(
        "ticket_snapshots",
        sa.Column("ticket_id", sa.BigInteger(), primary_key=True),
        sa.Column("ticket_number", sa.String(20)),
        sa.Column("title", sa.Text()),
        sa.Column("customer_id", sa.String(200)),
        sa.Column("customer_user_id", sa.String(200)),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.Column("current_queue", sa.String(200)),
        sa.Column("current_state", sa.String(50)),
        sa.Column("current_owner", sa.String(100)),
        sa.Column("first_response_at", sa.DateTime()),
        sa.Column("resolution_at", sa.DateTime()),
        sa.Column("is_closed", sa.Boolean(), server_default="false"),
        sa.Column("is_merged", sa.Boolean(), server_default="false"),
        sa.Column("confidence", sa.String(20), server_default="partial"),
        sa.Column("last_import_id", UUID(as_uuid=True), sa.ForeignKey("import_sessions.id")),
        sa.Column("updated_at_ts", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "ownership_periods",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ticket_id", sa.BigInteger(), sa.ForeignKey("ticket_snapshots.ticket_id"), nullable=False),
        sa.Column("owner", sa.String(100)),
        sa.Column("queue_name", sa.String(200)),
        sa.Column("team_prefix", sa.String(50)),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime()),
        sa.Column("duration_seconds", sa.Integer()),
        sa.Column("is_active", sa.Boolean(), server_default="false"),
    )
    op.create_index("ix_ownership_ticket_id", "ownership_periods", ["ticket_id"])

    op.create_table(
        "queue_periods",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ticket_id", sa.BigInteger(), sa.ForeignKey("ticket_snapshots.ticket_id"), nullable=False),
        sa.Column("queue_name", sa.String(200), nullable=False),
        sa.Column("team_prefix", sa.String(50)),
        sa.Column("entered_at", sa.DateTime(), nullable=False),
        sa.Column("exited_at", sa.DateTime()),
        sa.Column("duration_seconds", sa.Integer()),
        sa.Column("owner_count", sa.Integer(), server_default="0"),
    )
    op.create_index("ix_queue_ticket_id", "queue_periods", ["ticket_id"])

    op.create_table(
        "sla_definitions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("queue_pattern", sa.String(200)),
        sa.Column("priority", sa.String(50)),
        sa.Column("response_target_seconds", sa.Integer(), nullable=False),
        sa.Column("resolution_target_seconds", sa.Integer(), nullable=False),
        sa.Column("pause_on_pending", sa.Boolean(), server_default="true"),
        sa.Column("business_hours_only", sa.Boolean(), server_default="false"),
        sa.Column("business_hours", JSONB(), server_default="{}"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "sla_metrics",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("metric_name", sa.String(50), nullable=False),
        sa.Column("metric_seconds", sa.Integer()),
        sa.Column("sla_breached", sa.Boolean()),
        sa.Column("queue_name", sa.String(200)),
        sa.Column("owner", sa.String(100)),
        sa.Column("team_prefix", sa.String(50)),
        sa.Column("sla_definition_id", sa.Integer(), sa.ForeignKey("sla_definitions.id")),
        sa.Column("import_id", UUID(as_uuid=True), sa.ForeignKey("import_sessions.id")),
        sa.Column("confidence", sa.String(20)),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sla_metrics_ticket_id", "sla_metrics", ["ticket_id"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("actor_id", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(50)),
        sa.Column("resource_id", sa.String(100)),
        sa.Column("details", JSONB(), server_default="{}"),
        sa.Column("ip_address", INET()),
    )
    op.create_index("ix_audit_timestamp", "audit_log", ["timestamp"])

    op.create_table(
        "user_teams",
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_index("ix_ticket_events_import_ticket_seq", table_name="ticket_events")
    op.drop_index("ix_ticket_events_ticket_seq", table_name="ticket_events")
    op.drop_table("user_teams")
    op.drop_table("audit_log")
    op.drop_table("sla_metrics")
    op.drop_table("sla_definitions")
    op.drop_table("queue_periods")
    op.drop_table("ownership_periods")
    op.drop_table("ticket_snapshots")
    op.drop_table("ticket_events")
    op.drop_table("raw_events")
    op.drop_table("teams")
    op.drop_table("import_sessions")
    op.drop_table("users")
