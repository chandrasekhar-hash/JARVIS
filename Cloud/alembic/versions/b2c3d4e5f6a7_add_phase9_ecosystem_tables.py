"""Add Phase 9 Ecosystem tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-28 21:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Cloud Plugins Table
    op.create_table(
        "cloud_plugins",
        sa.Column("plugin_id", sa.String(length=64), nullable=False),
        sa.Column("publisher_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("sdk_version", sa.String(length=32), nullable=False),
        sa.Column("api_version", sa.String(length=32), nullable=False),
        sa.Column("minimum_runtime", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("capabilities_json", sa.Text(), nullable=False),
        sa.Column("package_url", sa.Text(), nullable=False),
        sa.Column("signature_b64", sa.Text(), nullable=False),
        sa.Column("downloads_count", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("is_trusted", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("plugin_id")
    )

    # 2. Cloud Webhook Subscriptions Table
    op.create_table(
        "cloud_webhook_subscriptions",
        sa.Column("subscription_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("target_url", sa.Text(), nullable=False),
        sa.Column("secret_token", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("subscription_id")
    )

    # 3. Cloud Developer Keys Table
    op.create_table(
        "cloud_developer_keys",
        sa.Column("key_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("api_key_hash", sa.String(length=128), nullable=False),
        sa.Column("key_prefix", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("scopes_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("expires_at", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("key_id")
    )


def downgrade() -> None:
    op.drop_table("cloud_developer_keys")
    op.drop_table("cloud_webhook_subscriptions")
    op.drop_table("cloud_plugins")
