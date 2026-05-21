"""Favorite queues + queue groups + dashboard presets + team operational fields.

Revision ID: 021_favorite_queues
Revises: 020_attachments
Create Date: 2026-05-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "021_favorite_queues"
down_revision: Union[str, None] = "020_attachments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- favorite_queues -------------------------------------------------
    op.create_table(
        "favorite_queues",
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("queue_name", sa.String(200), primary_key=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("starred_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )
    op.create_index("ix_favorite_queues_user", "favorite_queues", ["user_id"])

    # ---- queue_groups ----------------------------------------------------
    op.create_table(
        "queue_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("color", sa.String(20)),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )
    op.create_index("ix_queue_groups_user", "queue_groups", ["user_id"])
    op.create_index("ix_queue_groups_shared", "queue_groups", ["is_shared"])

    # ---- queue_group_items ----------------------------------------------
    op.create_table(
        "queue_group_items",
        sa.Column("group_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("queue_groups.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("queue_name", sa.String(200), primary_key=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )

    # ---- dashboard_presets ----------------------------------------------
    op.create_table(
        "dashboard_presets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("workspace_kind", sa.String(50), nullable=False,
                  server_default="custom"),
        sa.Column("queue_group_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("queue_groups.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("layout", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )
    op.create_index("ix_dashboard_presets_user", "dashboard_presets", ["user_id"])

    # ---- teams operational fields (additive) -----------------------------
    with op.batch_alter_table("teams") as batch:
        batch.add_column(sa.Column(
            "lead_user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"), nullable=True))
        batch.add_column(sa.Column("color", sa.String(20), nullable=True))
        batch.add_column(sa.Column("response_target_seconds", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("resolution_target_seconds", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("escalation_chain", postgresql.JSONB(),
                                   server_default=sa.text("'[]'::jsonb")))
        batch.add_column(sa.Column("queues", postgresql.JSONB(),
                                   server_default=sa.text("'[]'::jsonb")))


def downgrade() -> None:
    with op.batch_alter_table("teams") as batch:
        batch.drop_column("queues")
        batch.drop_column("escalation_chain")
        batch.drop_column("resolution_target_seconds")
        batch.drop_column("response_target_seconds")
        batch.drop_column("color")
        batch.drop_column("lead_user_id")
    op.drop_index("ix_dashboard_presets_user", table_name="dashboard_presets")
    op.drop_table("dashboard_presets")
    op.drop_table("queue_group_items")
    op.drop_index("ix_queue_groups_shared", table_name="queue_groups")
    op.drop_index("ix_queue_groups_user", table_name="queue_groups")
    op.drop_table("queue_groups")
    op.drop_index("ix_favorite_queues_user", table_name="favorite_queues")
    op.drop_table("favorite_queues")
