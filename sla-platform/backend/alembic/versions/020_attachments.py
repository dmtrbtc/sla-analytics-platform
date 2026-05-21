"""Add attachments table for enterprise file storage.

Revision ID: 020_attachments
Revises: 019_saas_tables
Create Date: 2026-05-20 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "020_attachments"
down_revision: Union[str, None] = "019_saas_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NOTE: previous version referenced a `tickets(id)` FK with Integer type.
    # No such table exists — the real ticket table is `ticket_snapshots` keyed
    # on a BigInteger `ticket_id`. The original FK definition caused alembic
    # to fail with UndefinedTableError on every container start, blocking the
    # entire backend boot. We drop the strict FK (attachments must outlive
    # ticket deletion anyway) and store ticket_id as a nullable BigInteger
    # the API filters on.
    op.create_table(
        "attachments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("stored_name", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100)),
        sa.Column("size_bytes", sa.BigInteger(), default=0),
        sa.Column("file_hash", sa.String(64)),
        sa.Column("ticket_id", sa.BigInteger(), nullable=True),
        sa.Column("import_id", sa.String(36), nullable=True),
        sa.Column("description", sa.Text()),
        sa.Column("uploaded_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), default=sa.func.now()),
    )
    op.create_index("ix_attachments_ticket", "attachments", ["ticket_id"])
    op.create_index("ix_attachments_import", "attachments", ["import_id"])
    op.create_index("ix_attachments_uploaded", "attachments", ["uploaded_by"])


def downgrade() -> None:
    op.drop_index("ix_attachments_uploaded")
    op.drop_index("ix_attachments_import")
    op.drop_index("ix_attachments_ticket")
    op.drop_table("attachments")
