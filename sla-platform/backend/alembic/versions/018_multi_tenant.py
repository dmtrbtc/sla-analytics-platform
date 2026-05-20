"""Enterprise multi-tenancy — organizations, quotas, branding, tenant isolation.

Adds:
  - organizations table
  - organization_quotas table
  - organization_branding table
  - organization_audit table
  - organization_id FK columns on users, import_sessions, sla_definitions, sla_metrics, teams

Revision ID: 018_multi_tenant
Revises: 017_performance_indexes
Create Date: 2026-05-20 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "018_multi_tenant"
down_revision: Union[str, None] = "017_performance_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Organizations
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Organization quotas
    op.create_table(
        "organization_quotas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("max_imports_per_day", sa.Integer(), default=50),
        sa.Column("max_storage_gb", sa.Integer(), default=10),
        sa.Column("max_exports_per_day", sa.Integer(), default=20),
        sa.Column("analytics_retention_days", sa.Integer(), default=90),
        sa.Column("max_users", sa.Integer(), default=25),
        sa.Column("created_at", sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Organization branding
    op.create_table(
        "organization_branding",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("logo_url", sa.String(500)),
        sa.Column("primary_color", sa.String(7), default="#1890ff"),
        sa.Column("secondary_color", sa.String(7), default="#52c41a"),
        sa.Column("report_header_template", sa.Text()),
        sa.Column("report_footer_template", sa.Text()),
        sa.Column("timezone", sa.String(100), default="UTC"),
        sa.Column("locale", sa.String(10), default="ru"),
        sa.Column("created_at", sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Organization audit
    op.create_table(
        "organization_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(50)),
        sa.Column("resource_id", sa.String(100)),
        sa.Column("details", postgresql.JSONB(), default=dict),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("created_at", sa.DateTime(timezone=True), default=sa.func.now()),
    )
    op.create_index("ix_org_audit_org_id", "organization_audit", ["organization_id"])
    op.create_index("ix_org_audit_created_at", "organization_audit", ["created_at"])

    # Add organization_id FK columns
    op.add_column("users", sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True))
    op.create_index("ix_users_organization_id", "users", ["organization_id"])

    op.add_column("import_sessions", sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True))
    op.create_index("ix_import_sessions_organization_id", "import_sessions", ["organization_id"])

    op.add_column("sla_definitions", sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True))
    op.create_index("ix_sla_definitions_organization_id", "sla_definitions", ["organization_id"])

    op.add_column("sla_metrics", sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True))
    op.create_index("ix_sla_metrics_organization_id", "sla_metrics", ["organization_id"])

    op.add_column("teams", sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True))
    op.create_index("ix_teams_organization_id", "teams", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_users_organization_id")
    op.drop_column("users", "organization_id")
    op.drop_index("ix_import_sessions_organization_id")
    op.drop_column("import_sessions", "organization_id")
    op.drop_index("ix_sla_definitions_organization_id")
    op.drop_column("sla_definitions", "organization_id")
    op.drop_index("ix_sla_metrics_organization_id")
    op.drop_column("sla_metrics", "organization_id")
    op.drop_index("ix_teams_organization_id")
    op.drop_column("teams", "organization_id")
    op.drop_index("ix_org_audit_created_at")
    op.drop_index("ix_org_audit_org_id")
    op.drop_table("organization_audit")
    op.drop_table("organization_branding")
    op.drop_table("organization_quotas")
    op.drop_table("organizations")
