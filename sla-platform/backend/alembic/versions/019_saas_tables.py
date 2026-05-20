"""SaaS tables — subscriptions, usage, API tokens, webhooks, SAML.

Adds:
  - subscription_plans
  - organization_subscriptions
  - usage_records
  - api_tokens
  - webhooks
  - saml_providers
  - saml_sessions

Revision ID: 019_saas_tables
Revises: 018_multi_tenant
Create Date: 2026-05-20 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "019_saas_tables"
down_revision: Union[str, None] = "018_multi_tenant"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Subscription plans
    op.create_table(
        "subscription_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("slug", sa.String(50), nullable=False, unique=True),
        sa.Column("description", sa.Text()),
        sa.Column("price_monthly_cents", sa.Integer(), default=0),
        sa.Column("price_yearly_cents", sa.Integer(), default=0),
        sa.Column("max_imports_per_day", sa.Integer(), default=10),
        sa.Column("max_storage_gb", sa.Integer(), default=5),
        sa.Column("max_exports_per_day", sa.Integer(), default=5),
        sa.Column("analytics_retention_days", sa.Integer(), default=30),
        sa.Column("max_users", sa.Integer(), default=5),
        sa.Column("max_queues", sa.Integer(), default=10),
        sa.Column("features", postgresql.JSONB(), default=dict),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), default=sa.func.now()),
    )

    # Organization subscriptions
    op.create_table(
        "organization_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subscription_plans.id"), nullable=False),
        sa.Column("status", sa.String(20), default="active"),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True)),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("canceled_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), default=sa.func.now()),
    )
    op.create_index("ix_subscriptions_org", "organization_subscriptions", ["organization_id"])

    # Usage records
    op.create_table(
        "usage_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric", sa.String(50), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), default=sa.func.now()),
    )
    op.create_index("ix_usage_org_metric", "usage_records", ["organization_id", "metric"])
    op.create_index("ix_usage_recorded_at", "usage_records", ["recorded_at"])

    # API tokens
    op.create_table(
        "api_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("permissions", postgresql.JSONB(), default=list),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_api_tokens_user", "api_tokens", ["user_id"])

    # Webhooks
    op.create_table(
        "webhooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("events", postgresql.JSONB(), default=list),
        sa.Column("secret", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), default=sa.func.now()),
    )
    op.create_index("ix_webhooks_org", "webhooks", ["organization_id"])

    # SAML providers
    op.create_table(
        "saml_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", sa.String(500), nullable=False),
        sa.Column("sso_url", sa.String(2000)),
        sa.Column("certificate", sa.Text()),
        sa.Column("metadata_json", postgresql.JSONB()),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), default=sa.func.now()),
    )

    # SAML sessions
    op.create_table(
        "saml_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("saml_providers.id"), nullable=False),
        sa.Column("session_index", sa.String(200)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("saml_sessions")
    op.drop_table("saml_providers")
    op.drop_index("ix_webhooks_org")
    op.drop_table("webhooks")
    op.drop_index("ix_api_tokens_user")
    op.drop_table("api_tokens")
    op.drop_index("ix_usage_recorded_at")
    op.drop_index("ix_usage_org_metric")
    op.drop_table("usage_records")
    op.drop_index("ix_subscriptions_org")
    op.drop_table("organization_subscriptions")
    op.drop_table("subscription_plans")
