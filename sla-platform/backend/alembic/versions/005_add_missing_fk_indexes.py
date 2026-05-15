"""Add missing FK column indexes identified in performance audit.

Revision ID: 005
Revises: 004_add_refresh_tokens
Create Date: 2026-05-15 07:30:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "005_add_missing_fk_indexes"
down_revision: Union[str, None] = "004_add_refresh_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEXES: list[tuple[str, str, list[str]]] = [
    ("ix_import_sessions_imported_by", "import_sessions", ["imported_by"]),
    ("ix_ticket_snapshots_last_import_id", "ticket_snapshots", ["last_import_id"]),
    ("ix_sla_definitions_created_by", "sla_definitions", ["created_by"]),
    ("ix_sla_metrics_sla_definition_id", "sla_metrics", ["sla_definition_id"]),
    ("ix_audit_log_actor_id", "audit_log", ["actor_id"]),
]


def upgrade() -> None:
    for name, table, columns in INDEXES:
        op.create_index(name, table, columns, unique=False)


def downgrade() -> None:
    for name, _, _ in reversed(INDEXES):
        op.drop_index(name)
