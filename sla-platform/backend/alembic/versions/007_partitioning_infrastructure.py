"""Optional: Add PostgreSQL partitioning infrastructure.

Creates the partition schema and meta table for managing partitioned
inheritance-based partitions on raw_events, ticket_events, and sla_metrics.

This migration is SAFE to run at any time — it does NOT alter existing
tables. Actual partition creation and trigger routing must be done
separately via partition_manager.py or manual SQL.

Revision ID: 007
Revises: 006_add_composite_secondary_idx
Create Date: 2026-05-15 07:45:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "007_partition_infra"
down_revision: Union[str, None] = "006_add_composite_secondary_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS partitions")
    op.execute("""
        CREATE TABLE IF NOT EXISTS partitions.partition_meta (
            table_name          TEXT NOT NULL,
            strategy            TEXT NOT NULL,
            partition_key       TEXT NOT NULL,
            partition_name      TEXT NOT NULL,
            partition_boundary  TEXT NOT NULL,
            created_at          TIMESTAMPTZ DEFAULT now(),
            is_active           BOOLEAN DEFAULT TRUE,
            PRIMARY KEY (table_name, partition_name)
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS partitions.partition_meta CASCADE")
    op.execute("DROP SCHEMA IF EXISTS partitions CASCADE")
