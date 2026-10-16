"""Create the Invitations.

Revision ID: b4e7a1c93d58
Revises: 2a9c4e7b1d35
Create Date: 2026-10-16 12:00:00.000000

Forward only (ADR 0020): add no reverse function.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b4e7a1c93d58"
down_revision: str | Sequence[str] | None = "2a9c4e7b1d35"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "invitation",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("issued_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_by", sa.BigInteger(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", sa.BigInteger(), nullable=True),
        sa.CheckConstraint("used_at IS NULL OR revoked_at IS NULL", name="used_or_revoked"),
        sa.ForeignKeyConstraint(["issued_by"], ["user_account.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["used_by"], ["user_account.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["revoked_by"], ["user_account.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invitation_email"), "invitation", ["email"], unique=False)
