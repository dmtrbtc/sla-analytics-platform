"""Add missing sla_metrics.import_id index

Revision ID: 002
Revises: 001
Create Date: 2026-05-13
"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_sla_metrics_import_id", "sla_metrics", ["import_id"])


def downgrade() -> None:
    op.drop_index("ix_sla_metrics_import_id", table_name="sla_metrics")
