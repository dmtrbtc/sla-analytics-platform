"""Add app_config table for admin-managed enterprise settings.

Revision ID: 009
Revises: 008_materialized_views
Create Date: 2026-05-15 08:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "009_app_config"
down_revision: Union[str, None] = "008_materialized_views"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_config",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("config_key", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("config_value", postgresql.JSONB, nullable=False, default=dict),
        sa.Column("description", sa.Text),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.Column("updated_by", sa.String(255)),
    )
    # Seed default configurations
    conn = op.get_bind()
    conn.exec_driver_sql("""
        INSERT INTO app_config (config_key, config_value, description, updated_at) VALUES
        ('business_hours_default', '{"monday":{"start":"09:00","end":"18:00"},"tuesday":{"start":"09:00","end":"18:00"},"wednesday":{"start":"09:00","end":"18:00"},"thursday":{"start":"09:00","end":"18:00"},"friday":{"start":"09:00","end":"18:00"},"saturday":null,"sunday":null}'::jsonb, 'Default business hours schedule', now()),
        ('holidays', '[]'::jsonb, 'List of holiday dates', now()),
        ('retention_days', '"365"'::jsonb, 'Number of days to retain import data before archival', now()),
        ('notification_thresholds', '{"sla_breach_warning_pct":80,"queue_backlog_warning":100}'::jsonb, 'Alert thresholds', now()),
        ('queue_mappings', '{}'::jsonb, 'Queue name aliases and routing rules', now())
    """)


def downgrade() -> None:
    op.drop_table("app_config")
