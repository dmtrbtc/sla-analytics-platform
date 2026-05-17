"""Add sla_risk_score, risk_level, risk_reason columns to sla_metrics.

Revision ID: 012_sla_risk
Revises: 011_sla_queue_rules
Create Date: 2026-05-17 23:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "012_sla_risk"
down_revision: Union[str, None] = "011_sla_queue_rules"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sla_metrics", sa.Column("sla_risk_score", sa.Integer, nullable=True))
    op.add_column("sla_metrics", sa.Column("risk_level", sa.String(20), nullable=True))
    op.add_column("sla_metrics", sa.Column("risk_reason", sa.Text, nullable=True))
    op.create_index("ix_sla_metrics_risk_level", "sla_metrics", ["risk_level"])
    op.create_index("ix_sla_metrics_queue_risk", "sla_metrics", ["queue_name", "risk_level"])


def downgrade() -> None:
    op.drop_index("ix_sla_metrics_queue_risk")
    op.drop_index("ix_sla_metrics_risk_level")
    op.drop_column("sla_metrics", "risk_reason")
    op.drop_column("sla_metrics", "risk_level")
    op.drop_column("sla_metrics", "sla_risk_score")
