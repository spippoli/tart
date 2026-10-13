"""Add record visibility: Withdrawal, Merge, and Redaction states.

Revision ID: 8e4b1f6c2d90
Revises: d3a7c5e91f28
Create Date: 2026-10-13 18:00:00.000000

Forward only (ADR 0020): add no reverse function.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8e4b1f6c2d90"
down_revision: str | Sequence[str] | None = "d3a7c5e91f28"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("record", sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("record", sa.Column("merged_into", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        op.f("fk_record_merged_into_record"),
        "record",
        "record",
        ["merged_into"],
        ["id"],
        initially="DEFERRED",
        deferrable=True,
    )
    op.create_check_constraint(
        op.f("ck_record_not_merged_into_itself"), "record", "merged_into <> id"
    )
    op.create_table(
        "redaction",
        sa.Column("revision_id", sa.BigInteger(), nullable=False),
        sa.Column("operation", sa.Integer(), nullable=False),
        sa.Column("redacted_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("operation >= 0", name=op.f("ck_redaction_operation_index")),
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["revision.id"],
            name=op.f("fk_redaction_revision_id_revision"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.PrimaryKeyConstraint("revision_id", "operation", name=op.f("pk_redaction")),
    )
