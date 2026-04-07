"""Autopilot settings and run logs

Revision ID: 20260406_0002
Revises: 20260403_0001
Create Date: 2026-04-06 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260406_0002"
down_revision: Union[str, None] = "20260403_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "autopilot_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("auto_submit", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("paid_only", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("legit_only", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("max_applications_per_day", sa.Integer(), nullable=False, server_default=sa.text("5")),
        sa.Column("limit_per_company", sa.Integer(), nullable=False, server_default=sa.text("25")),
        sa.Column("greenhouse_companies", postgresql.JSON()),
        sa.Column("lever_companies", postgresql.JSON()),
        sa.Column("title_keywords", postgresql.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_autopilot_settings_user_id", "autopilot_settings", ["user_id"], unique=True)

    op.create_table(
        "autopilot_run_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trigger", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("jobs_seen", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("jobs_qualified", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("applications_queued", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("message", sa.Text()),
        sa.Column("details_json", postgresql.JSON()),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_autopilot_run_logs_user_id", "autopilot_run_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_autopilot_run_logs_user_id", table_name="autopilot_run_logs")
    op.drop_table("autopilot_run_logs")

    op.drop_index("ix_autopilot_settings_user_id", table_name="autopilot_settings")
    op.drop_table("autopilot_settings")
