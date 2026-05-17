"""Add sla_queue_rules table for per-queue SLA governance.

Revision ID: 011_sla_queue_rules
Revises: 010_task_audit
Create Date: 2026-05-17 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "011_sla_queue_rules"
down_revision: Union[str, None] = "010_task_audit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sla_queue_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("queue_pattern", sa.String(200), nullable=False),
        sa.Column("priority", sa.Integer, server_default="0"),
        sa.Column("response_target_seconds", sa.Integer, nullable=False),
        sa.Column("resolution_target_seconds", sa.Integer, nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("description", sa.Text),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sla_queue_rules_queue_pattern", "sla_queue_rules", ["queue_pattern"])
    op.create_index("ix_sla_queue_rules_is_active", "sla_queue_rules", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_sla_queue_rules_is_active")
    op.drop_index("ix_sla_queue_rules_queue_pattern")
    op.drop_table("sla_queue_rules")
