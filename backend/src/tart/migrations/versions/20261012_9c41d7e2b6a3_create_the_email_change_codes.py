"""Create the email change codes.

Revision ID: 9c41d7e2b6a3
Revises: 5b2e9f04a7c1
Create Date: 2026-10-12 20:00:00.000000

Forward only (ADR 0020): add no reverse function.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9c41d7e2b6a3"
down_revision: str | Sequence[str] | None = "5b2e9f04a7c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "email_change_code",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("new_email", sa.Text(), nullable=False),
        sa.Column("code_hash", sa.LargeBinary(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("wrong_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name=op.f("fk_email_change_code_user_id_user_account"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_email_change_code")),
    )
