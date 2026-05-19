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


def _create_index_if_not_exists(index_name: str, table: str, columns: list[str]) -> None:
    sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({', '.join(columns)})"
    op.execute(sql)


def upgrade() -> None:
    _create_index_if_not_exists("ix_sla_metrics_metric_breached_time", "sla_metrics", ["metric_name", "sla_breached", "computed_at"])
    _create_index_if_not_exists("ix_sla_metrics_risk_level_time", "sla_metrics", ["risk_level", "computed_at"])
    _create_index_if_not_exists("ix_sla_metrics_team_metric", "sla_metrics", ["team_prefix", "metric_name"])
    _create_index_if_not_exists("ix_sla_metrics_ticket_metric", "sla_metrics", ["ticket_id", "metric_name"])
    _create_index_if_not_exists("ix_sla_metrics_import_metric", "sla_metrics", ["import_id", "metric_name"])


def downgrade() -> None:
    for name in ("ix_sla_metrics_metric_breached_time", "ix_sla_metrics_risk_level_time", "ix_sla_metrics_team_metric", "ix_sla_metrics_ticket_metric", "ix_sla_metrics_import_metric"):
        op.execute(f"DROP INDEX IF EXISTS {name}")
