"""Add materialized views for dashboard and analytics performance.

Views:
  - mv_sla_summary_daily: Daily SLA metric aggregates
  - mv_queue_performance_daily: Daily queue performance aggregates
  - mv_team_metrics_daily: Daily team performance aggregates

Revision ID: 008
Revises: 007_partition_infra
Create Date: 2026-05-15 08:15:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "008_materialized_views"
down_revision: Union[str, None] = "007_partition_infra"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


VIEWS: list[tuple[str, str]] = [
    (
        "mv_sla_summary_daily",
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_sla_summary_daily AS
        SELECT
            date_trunc('day', computed_at) AS day,
            metric_name,
            queue_name,
            team_prefix,
            COUNT(*) AS total_metrics,
            COUNT(*) FILTER (WHERE sla_breached) AS breached_count,
            AVG(metric_seconds)::numeric(10,2) AS avg_seconds,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY metric_seconds)::numeric(10,2) AS median_seconds
        FROM sla_metrics
        GROUP BY date_trunc('day', computed_at), metric_name, queue_name, team_prefix
        WITH DATA
        """,
    ),
    (
        "mv_queue_performance_daily",
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_queue_performance_daily AS
        SELECT
            date_trunc('day', entered_at) AS day,
            queue_name,
            team_prefix,
            COUNT(DISTINCT ticket_id) AS distinct_tickets,
            COUNT(*) AS total_visits,
            AVG(duration_seconds)::numeric(10,2) AS avg_duration_seconds,
            SUM(duration_seconds)::numeric(10,2) AS total_duration_seconds
        FROM queue_periods
        GROUP BY date_trunc('day', entered_at), queue_name, team_prefix
        WITH DATA
        """,
    ),
    (
        "mv_team_metrics_daily",
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_team_metrics_daily AS
        SELECT
            date_trunc('day', op.start_time) AS day,
            op.team_prefix,
            op.owner,
            COUNT(DISTINCT op.ticket_id) AS tickets_handled,
            AVG(op.duration_seconds)::numeric(10,2) AS avg_ownership_seconds,
            SUM(op.duration_seconds)::numeric(10,2) AS total_ownership_seconds
        FROM ownership_periods op
        GROUP BY date_trunc('day', op.start_time), op.team_prefix, op.owner
        WITH DATA
        """,
    ),
]

INDEXES: list[tuple[str, str, list[str]]] = [
    ("ix_mv_sla_summary_day", "mv_sla_summary_daily", ["day"]),
    ("ix_mv_queue_perf_day", "mv_queue_performance_daily", ["day"]),
    ("ix_mv_team_metrics_day", "mv_team_metrics_daily", ["day"]),
]


def upgrade() -> None:
    for name, sql in VIEWS:
        op.execute(sql)
    for name, table, columns in INDEXES:
        op.create_index(name, table, columns, unique=False, postgresql_using="btree")


def downgrade() -> None:
    for name, _, _ in INDEXES:
        op.drop_index(name, materialized_view=True)
    for name, _ in reversed(VIEWS):
        op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {name} CASCADE")
