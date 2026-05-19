"""Performance indexes — composite indexes for real query patterns from analytics, dashboard, and import pipeline.

Indexes added:
  - import_sessions(status, created_at) — session listing with status filter
  - ticket_events(owner_name, event_time) — owner analytics queries
  - ticket_events(queue_name, event_time) — queue analytics queries
  - raw_events(duplicate_key) — deduplication lookups during normalization
  - audit_log(resource_type, resource_id) — audit queries by resource
  - sla_metrics(computed_at, sla_breached) — dashboard breach trend queries
  - sla_metrics(queue_name, computed_at) — queue SLA analytics
  - ticket_snapshots(is_closed) — open ticket filtering
  - ticket_snapshots(current_queue) — queue distribution queries
  - ticket_snapshots(is_closed, created_at) — aging ticket analysis
  - ownership_periods(owner, start_time) — owner workload queries
  - queue_periods(entered_at, queue_name) — queue bottleneck analysis
  - queue_periods(team_prefix, entered_at) — team queue analytics

Revision ID: 017_performance_indexes
Revises: 016_sla_engine_v2
Create Date: 2026-05-19 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "017_performance_indexes"
down_revision: Union[str, None] = "016_sla_engine_v2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_index_if_not_exists(index_name: str, table: str, columns: list[str]) -> None:
    sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({', '.join(columns)})"
    op.execute(sql)


def upgrade() -> None:
    _create_index_if_not_exists("ix_import_sessions_status_created", "import_sessions", ["status", "created_at"])
    _create_index_if_not_exists("ix_ticket_events_owner_time", "ticket_events", ["owner_name", "event_time"])
    _create_index_if_not_exists("ix_ticket_events_queue_time", "ticket_events", ["queue_name", "event_time"])
    _create_index_if_not_exists("ix_raw_events_duplicate_key", "raw_events", ["duplicate_key"])
    _create_index_if_not_exists("ix_audit_log_resource", "audit_log", ["resource_type", "resource_id"])
    _create_index_if_not_exists("ix_sla_metrics_computed_breached", "sla_metrics", ["computed_at", "sla_breached"])
    _create_index_if_not_exists("ix_sla_metrics_queue_computed", "sla_metrics", ["queue_name", "computed_at"])
    _create_index_if_not_exists("ix_ticket_snapshots_is_closed", "ticket_snapshots", ["is_closed"])
    _create_index_if_not_exists("ix_ticket_snapshots_current_queue", "ticket_snapshots", ["current_queue"])
    _create_index_if_not_exists("ix_ticket_snapshots_closed_created", "ticket_snapshots", ["is_closed", "created_at"])
    _create_index_if_not_exists("ix_ownership_periods_owner_start", "ownership_periods", ["owner", "start_time"])
    _create_index_if_not_exists("ix_queue_periods_entered_queue", "queue_periods", ["entered_at", "queue_name"])
    _create_index_if_not_exists("ix_queue_periods_team_entered", "queue_periods", ["team_prefix", "entered_at"])


def downgrade() -> None:
    for name in (
        "ix_import_sessions_status_created",
        "ix_ticket_events_owner_time",
        "ix_ticket_events_queue_time",
        "ix_raw_events_duplicate_key",
        "ix_audit_log_resource",
        "ix_sla_metrics_computed_breached",
        "ix_sla_metrics_queue_computed",
        "ix_ticket_snapshots_is_closed",
        "ix_ticket_snapshots_current_queue",
        "ix_ticket_snapshots_closed_created",
        "ix_ownership_periods_owner_start",
        "ix_queue_periods_entered_queue",
        "ix_queue_periods_team_entered",
    ):
        op.execute(f"DROP INDEX IF EXISTS {name}")
