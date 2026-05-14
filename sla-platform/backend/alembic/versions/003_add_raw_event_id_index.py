"""Add missing index on ticket_events.raw_event_id (FK perf)

Revision ID: 003
Revises: 002
Create Date: 2026-05-14
"""
from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_ticket_events_raw_event_id", "ticket_events", ["raw_event_id"])


def downgrade() -> None:
    op.drop_index("ix_ticket_events_raw_event_id", table_name="ticket_events")
