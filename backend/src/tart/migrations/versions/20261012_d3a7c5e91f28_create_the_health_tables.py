"""Create the health tables: last operation successes and Operator alerts.

Revision ID: d3a7c5e91f28
Revises: 6b8d2f4e1a07
Create Date: 2026-10-12 22:00:00.000000

Forward only (ADR 0020): add no reverse function.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d3a7c5e91f28"
down_revision: str | Sequence[str] | None = "6b8d2f4e1a07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "operation_success",
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column("succeeded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "operation IN ('backup', 'verify')",
            name=op.f("ck_operation_success_operation_allowed"),
        ),
        sa.PrimaryKeyConstraint("operation", name=op.f("pk_operation_success")),
    )
    op.create_table(
        "operator_alert",
        sa.Column("check_key", sa.Text(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("check_key", name=op.f("pk_operator_alert")),
    )
