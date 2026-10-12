"""Create the passkeys and their challenges.

Revision ID: 5b2e9f04a7c1
Revises: d8aee55236e7
Create Date: 2026-10-11 23:30:00.000000

Forward only (ADR 0020): add no reverse function.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "5b2e9f04a7c1"
down_revision: str | Sequence[str] | None = "d8aee55236e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "passkey",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("credential_id", sa.LargeBinary(), nullable=False),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column("sign_count", sa.BigInteger(), nullable=False),
        sa.Column("transports", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name=op.f("fk_passkey_user_id_user_account"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_passkey")),
        sa.UniqueConstraint("credential_id", name=op.f("uq_passkey_credential_id")),
    )
    op.create_index(op.f("ix_passkey_user_id"), "passkey", ["user_id"], unique=False)
    op.create_table(
        "passkey_challenge",
        sa.Column("challenge_hash", sa.LargeBinary(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name=op.f("fk_passkey_challenge_user_id_user_account"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("challenge_hash", name=op.f("pk_passkey_challenge")),
    )
    op.create_index(
        op.f("ix_passkey_challenge_expires_at"), "passkey_challenge", ["expires_at"], unique=False
    )
