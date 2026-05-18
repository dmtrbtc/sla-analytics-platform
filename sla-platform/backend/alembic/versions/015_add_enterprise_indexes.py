"""Add enterprise-grade indexes for performance hardening.

Indexes added:
  - ticket_snapshots(current_state) — state-based filtering
  - ticket_snapshots(current_owner) — owner-based analytics
  - ticket_events(event_type, event_time) — event-based filters
  - ownership_periods(team_prefix, start_time) — team analytics
  - sla_metrics(queue_name, metric_name, computed_at) — queue-level SLA
  - queue_periods(queue_name, entered_at) — queue analytics composite
  - ticket_events(ticket_id, event_time) — timeline queries

Revision ID: 015_enterprise_idx
Revises: 014_analytics_idx
Create Date: 2026-05-18 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "015_enterprise_idx"
down_revision: Union[str, None] = "014_analytics_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ticket_snapshots state-based filtering
    op.create_index(
        "ix_ticket_snapshots_current_state",
        "ticket_snapshots",
        ["current_state"],
        unique=False,
    )
    # ticket_snapshots owner-based analytics
    op.create_index(
        "ix_ticket_snapshots_current_owner",
        "ticket_snapshots",
        ["current_owner"],
        unique=False,
    )
    # ticket_events event_type + event_time composite
    op.create_index(
        "ix_ticket_events_type_time",
        "ticket_events",
        ["event_type", "event_time"],
        unique=False,
    )
    # ticket_events ticket_id + event_time for timeline
    op.create_index(
        "ix_ticket_events_ticket_time",
        "ticket_events",
        ["ticket_id", "event_time"],
        unique=False,
    )
    # ownership_periods team analytics
    op.create_index(
        "ix_ownership_periods_team_start",
        "ownership_periods",
        ["team_prefix", "start_time"],
        unique=False,
    )
    # sla_metrics queue-level composite
    op.create_index(
        "ix_sla_metrics_queue_metric_time",
        "sla_metrics",
        ["queue_name", "metric_name", "computed_at"],
        unique=False,
    )
    # queue_periods queue + entered_at composite
    op.create_index(
        "ix_queue_periods_queue_entered",
        "queue_periods",
        ["queue_name", "entered_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ticket_snapshots_current_state")
    op.drop_index("ix_ticket_snapshots_current_owner")
    op.drop_index("ix_ticket_events_type_time")
    op.drop_index("ix_ticket_events_ticket_time")
    op.drop_index("ix_ownership_periods_team_start")
    op.drop_index("ix_sla_metrics_queue_metric_time")
    op.drop_index("ix_queue_periods_queue_entered")
