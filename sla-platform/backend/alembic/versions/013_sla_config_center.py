"""Add business_calendars, sla_escalation_rules, calendar_id on sla_queue_rules.

Revision ID: 013_sla_config
Revises: 012_sla_risk
Create Date: 2026-05-17 23:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = "013_sla_config"
down_revision: Union[str, None] = "012_sla_risk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "business_calendars",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("timezone", sa.String(100), server_default="UTC"),
        sa.Column("workdays", JSONB, server_default='{"monday":true,"tuesday":true,"wednesday":true,"thursday":true,"friday":true,"saturday":false,"sunday":false}'),
        sa.Column("start_time", sa.String(10), server_default="09:00"),
        sa.Column("end_time", sa.String(10), server_default="18:00"),
        sa.Column("holidays_json", JSONB, server_default="[]"),
        sa.Column("is_24x7", sa.Boolean, server_default="false"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("description", sa.Text),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_business_calendars_is_active", "business_calendars", ["is_active"])

    op.create_table(
        "sla_escalation_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("sla_rule_id", UUID(as_uuid=True), sa.ForeignKey("sla_queue_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("threshold_percent", sa.Integer, nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("notify_email", sa.String(500)),
        sa.Column("notify_telegram", sa.String(500)),
        sa.Column("webhook_url", sa.String(1000)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_escalation_sla_rule", "sla_escalation_rules", ["sla_rule_id"])
    op.create_index("ix_escalation_severity", "sla_escalation_rules", ["severity"])

    op.add_column("sla_queue_rules", sa.Column("calendar_id", UUID(as_uuid=True), sa.ForeignKey("business_calendars.id"), nullable=True))
    op.create_index("ix_sla_queue_rules_calendar", "sla_queue_rules", ["calendar_id"])


def downgrade() -> None:
    op.drop_index("ix_sla_queue_rules_calendar")
    op.drop_column("sla_queue_rules", "calendar_id")
    op.drop_index("ix_escalation_severity")
    op.drop_index("ix_escalation_sla_rule")
    op.drop_table("sla_escalation_rules")
    op.drop_index("ix_business_calendars_is_active")
    op.drop_table("business_calendars")
