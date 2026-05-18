"""Add composite indexes for analytics and operational intelligence queries.

Indexes added:
  - sla_metrics(computed_at, sla_breached, risk_level, queue_name) — overview, heatmap, risks
  - queue_periods(entered_at) — avg queue wait time

Revision ID: 014_analytics_idx
Revises: 013_sla_config
Create Date: 2026-05-18 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "014_analytics_idx"
down_revision: Union[str, None] = "013_sla_config"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_sla_metrics_analytics_overview",
        "sla_metrics",
        ["computed_at", "sla_breached", "risk_level", "queue_name"],
        unique=False,
    )
    op.create_index(
        "ix_queue_periods_entered_at",
        "queue_periods",
        ["entered_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_sla_metrics_analytics_overview")
    op.drop_index("ix_queue_periods_entered_at")
