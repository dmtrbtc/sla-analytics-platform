"""Enterprise SLA Engine V2 — indexes for V2 metrics, risk columns, team_prefix.

Indexes added:
  - sla_metrics(metric_name, sla_breached, computed_at) — V2 metric filtering
  - sla_metrics(risk_level, computed_at) — risk-based queries
  - sla_metrics(team_prefix, metric_name) — team SLA analytics
  - sla_metrics(ticket_id, metric_name) — per-ticket V2 metrics
  - sla_metrics(import_id, metric_name) — per-import V2 metrics

Columns populated (no schema change — columns already exist from migration 012):
  - sla_metrics.sla_risk_score (was NULL, now computed by MetricsEngine V2)
  - sla_metrics.risk_level (was NULL, now computed by MetricsEngine V2)
  - sla_metrics.risk_reason (was NULL, now computed by MetricsEngine V2)
  - sla_metrics.team_prefix (was NULL, now populated from queue/owner periods)

Revision ID: 016_sla_engine_v2
Revises: 015_enterprise_idx
Create Date: 2026-05-19 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "016_sla_engine_v2"
down_revision: Union[str, None] = "015_enterprise_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # sla_metrics V2 metric filtering composite
    op.create_index(
        "ix_sla_metrics_metric_breached_time",
        "sla_metrics",
        ["metric_name", "sla_breached", "computed_at"],
        unique=False,
    )
    # sla_metrics risk-level queries
    op.create_index(
        "ix_sla_metrics_risk_level_time",
        "sla_metrics",
        ["risk_level", "computed_at"],
        unique=False,
    )
    # sla_metrics team SLA analytics
    op.create_index(
        "ix_sla_metrics_team_metric",
        "sla_metrics",
        ["team_prefix", "metric_name"],
        unique=False,
    )
    # sla_metrics per-ticket V2 metrics
    op.create_index(
        "ix_sla_metrics_ticket_metric",
        "sla_metrics",
        ["ticket_id", "metric_name"],
        unique=False,
    )
    # sla_metrics per-import V2 metrics
    op.create_index(
        "ix_sla_metrics_import_metric",
        "sla_metrics",
        ["import_id", "metric_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_sla_metrics_metric_breached_time")
    op.drop_index("ix_sla_metrics_risk_level_time")
    op.drop_index("ix_sla_metrics_team_metric")
    op.drop_index("ix_sla_metrics_ticket_metric")
    op.drop_index("ix_sla_metrics_import_metric")
