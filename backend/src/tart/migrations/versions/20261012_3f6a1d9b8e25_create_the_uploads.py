"""Create the uploads.

Revision ID: 3f6a1d9b8e25
Revises: 9c41d7e2b6a3
Create Date: 2026-10-12 21:00:00.000000

Forward only (ADR 0020): add no reverse function.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "3f6a1d9b8e25"
down_revision: str | Sequence[str] | None = "9c41d7e2b6a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "upload",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("size", sa.BigInteger(), nullable=True),
        sa.Column("format", sa.Text(), nullable=True),
        sa.Column("renditions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("suggestions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('processing', 'ready', 'rejected')",
            name=op.f("ck_upload_status_allowed"),
        ),
        sa.CheckConstraint(
            "format IN ('jpeg', 'png', 'webp', 'avif', 'heic', 'pdf')",
            name=op.f("ck_upload_format_allowed"),
        ),
        sa.CheckConstraint(
            "(status = 'rejected') = (error IS NOT NULL)",
            name=op.f("ck_upload_error_when_rejected"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user_account.id"], name=op.f("fk_upload_user_id_user_account")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_upload")),
    )
    op.create_index("ix_upload_created_at", "upload", ["created_at"], unique=False)
    op.create_index("ix_upload_user_id", "upload", ["user_id"], unique=False)
