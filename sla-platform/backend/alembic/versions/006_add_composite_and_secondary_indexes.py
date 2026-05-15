"""Add composite and secondary indexes for query performance.

Composite indexes target common query patterns:
- ticket_events(import_id, ticket_id)
- sla_metrics(import_id, metric_name)
- ownership_periods(ticket_id, start_time)
- queue_periods(ticket_id, entered_at)

Secondary indexes target frequently filtered columns.

Revision ID: 006
Revises: 005_add_missing_fk_indexes
Create Date: 2026-05-15 07:35:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "006_add_composite_secondary_idx"
down_revision: Union[str, None] = "005_add_missing_fk_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COMPOSITE_INDEXES: list[tuple[str, str, list[str]]] = [
    ("ix_ticket_events_import_ticket", "ticket_events", ["import_id", "ticket_id"]),
    ("ix_sla_metrics_import_metric", "sla_metrics", ["import_id", "metric_name"]),
    ("ix_ownership_periods_ticket_start", "ownership_periods", ["ticket_id", "start_time"]),
    ("ix_queue_periods_ticket_entered", "queue_periods", ["ticket_id", "entered_at"]),
]

SECONDARY_INDEXES: list[tuple[str, str, list[str]]] = [
    ("ix_raw_events_event_name", "raw_events", ["event_name"]),
    ("ix_raw_events_queue_name", "raw_events", ["queue_name"]),
    ("ix_raw_events_event_time", "raw_events", ["event_time"]),
    ("ix_ticket_events_event_type", "ticket_events", ["event_type"]),
    ("ix_ticket_snapshots_is_closed", "ticket_snapshots", ["is_closed"]),
    ("ix_sla_metrics_metric_name", "sla_metrics", ["metric_name"]),
    ("ix_sla_metrics_sla_breached", "sla_metrics", ["sla_breached"]),
    ("ix_teams_queue_prefix", "teams", ["queue_prefix"]),
]


def upgrade() -> None:
    for name, table, columns in COMPOSITE_INDEXES:
        op.create_index(name, table, columns, unique=False)
    for name, table, columns in SECONDARY_INDEXES:
        op.create_index(name, table, columns, unique=False)


def downgrade() -> None:
    all_indexes = COMPOSITE_INDEXES + SECONDARY_INDEXES
    for name, _, _ in reversed(all_indexes):
        op.drop_index(name)
