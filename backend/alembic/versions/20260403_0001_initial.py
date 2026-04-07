"""Initial tables

Revision ID: 20260403_0001
Revises:
Create Date: 2026-04-03 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260403_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clerk_user_id", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_users_clerk_user_id", "users", ["clerk_user_id"], unique=True)

    op.create_table(
        "parsed_resumes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_filename", sa.String(length=255)),
        sa.Column("file_path", sa.String(length=1024)),
        sa.Column("raw_text", sa.Text()),
        sa.Column("parsed_json", postgresql.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_parsed_resumes_user_id", "parsed_resumes", ["user_id"], unique=False)

    op.create_table(
        "scraped_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_job_id", sa.String(length=128)),
        sa.Column("job_title", sa.String(length=255), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255)),
        sa.Column("employment_type", sa.String(length=64)),
        sa.Column("description", sa.Text()),
        sa.Column("required_skills", postgresql.JSON()),
        sa.Column("application_url", sa.String(length=1024), nullable=False),
        sa.Column("posted_date", sa.Date()),
        sa.Column("scraped_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_scraped_jobs_source_job_id", "scraped_jobs", ["source_job_id"], unique=False)

    op.create_table(
        "application_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True)),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("result_json", postgresql.JSON()),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["job_id"], ["scraped_jobs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_application_logs_user_id", "application_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_application_logs_user_id", table_name="application_logs")
    op.drop_table("application_logs")
    op.drop_index("ix_scraped_jobs_source_job_id", table_name="scraped_jobs")
    op.drop_table("scraped_jobs")
    op.drop_index("ix_parsed_resumes_user_id", table_name="parsed_resumes")
    op.drop_table("parsed_resumes")
    op.drop_index("ix_users_clerk_user_id", table_name="users")
    op.drop_table("users")
