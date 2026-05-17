"""Add task_audit table for Celery task monitoring.

Revision ID: 010_task_audit
Revises: 009_app_config
Create Date: 2026-05-15 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "010_task_audit"
down_revision: Union[str, None] = "009_app_config"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_audit",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.String(255), nullable=False),
        sa.Column("task_name", sa.String(255), nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("duration_ms", sa.Float, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_task_audit_task_name_started_at", "task_audit", ["task_name", "started_at"])
    op.create_index("ix_task_audit_status", "task_audit", ["status"])


def downgrade() -> None:
    op.drop_index("ix_task_audit_status")
    op.drop_index("ix_task_audit_task_name_started_at")
    op.drop_table("task_audit")
