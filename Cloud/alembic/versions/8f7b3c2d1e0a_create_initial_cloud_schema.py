"""Create initial cloud schema

Revision ID: 8f7b3c2d1e0a
Revises: 
Create Date: 2026-07-28 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "8f7b3c2d1e0a"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Cloud Users Table
    op.create_table(
        "cloud_users",
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=256), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.Column("preferences_json", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("user_id")
    )

    # 2. Cloud Devices Table
    op.create_table(
        "cloud_devices",
        sa.Column("device_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("device_name", sa.String(length=128), nullable=False),
        sa.Column("platform", sa.String(length=64), nullable=False),
        sa.Column("architecture", sa.String(length=64), nullable=False),
        sa.Column("os_version", sa.String(length=64), nullable=False),
        sa.Column("app_version", sa.String(length=64), nullable=False),
        sa.Column("public_key", sa.Text(), nullable=False),
        sa.Column("public_key_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("trust_state", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["cloud_users.user_id"]),
        sa.PrimaryKeyConstraint("device_id")
    )

    # 3. Cloud Sessions Table
    op.create_table(
        "cloud_sessions",
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.Float(), nullable=False),
        sa.Column("refresh_expires_at", sa.Float(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("session_id")
    )

    # 4. Cloud Audit Logs Table
    op.create_table(
        "cloud_audit_logs",
        sa.Column("log_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("device_id", sa.String(length=64), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("log_id")
    )

    # 5. Cloud Configurations Table
    op.create_table(
        "cloud_configurations",
        sa.Column("config_key", sa.String(length=128), nullable=False),
        sa.Column("config_value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("config_key")
    )


def downgrade() -> None:
    op.drop_table("cloud_configurations")
    op.drop_table("cloud_audit_logs")
    op.drop_table("cloud_sessions")
    op.drop_table("cloud_devices")
    op.drop_table("cloud_users")
