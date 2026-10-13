"""Create the Users, sessions, one-time codes, and rate-limit counters.

Revision ID: d8aee55236e7
Revises: 7a0e3c5b9d21
Create Date: 2026-10-11 22:46:21.659041

Forward only (ADR 0020): add no reverse function.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d8aee55236e7"
down_revision: str | Sequence[str] | None = "7a0e3c5b9d21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_event",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("key_hash", sa.LargeBinary(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rate_limit_event")),
    )
    op.create_index(
        op.f("ix_rate_limit_event_expires_at"), "rate_limit_event", ["expires_at"], unique=False
    )
    op.create_index(
        op.f("ix_rate_limit_event_name"),
        "rate_limit_event",
        ["name", "key_hash", "at"],
        unique=False,
    )
    op.create_table(
        "sign_in_code",
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("code_hash", sa.LargeBinary(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("wrong_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("email", name=op.f("pk_sign_in_code")),
    )
    op.create_table(
        "user_account",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("preferred_language", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspension_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "(suspended_at IS NULL) = (suspension_reason IS NULL)",
            name=op.f("ck_user_account_suspension_complete"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_account")),
        sa.UniqueConstraint("email", name=op.f("uq_user_account_email")),
    )
    op.create_table(
        "user_role",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.CheckConstraint("role IN ('moderator')", name=op.f("ck_user_role_role_allowed")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name=op.f("fk_user_role_user_id_user_account"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "role", name=op.f("pk_user_role")),
    )
    op.create_table(
        "user_session",
        sa.Column("id_hash", sa.LargeBinary(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name=op.f("fk_user_session_user_id_user_account"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id_hash", name=op.f("pk_user_session")),
    )
    op.create_index(op.f("ix_user_session_user_id"), "user_session", ["user_id"], unique=False)
