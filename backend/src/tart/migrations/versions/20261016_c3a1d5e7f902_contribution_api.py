"""Add the contribution API's tables: terms acceptances, Submission uploads, retry and
conversion links, stubs, deleted files, and weighted rate-limit events.

Revision ID: c3a1d5e7f902
Revises: b4e7a1c93d58
Create Date: 2026-10-16 15:00:00.000000

Forward only (ADR 0020): add no reverse function.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c3a1d5e7f902"
down_revision: str | Sequence[str] | None = "b4e7a1c93d58"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_EVENTS = (
    "'submitted', 'revised', 'resubmitted', 'approved', 'rejected', "
    "'changes_requested', 'retracted', 'expired'"
)
NEW_EVENTS = OLD_EVENTS + ", 'retry_of', 'retried_in', 'conversion_of', 'converted_into'"


def upgrade() -> None:
    op.create_table(
        "user_terms_acceptance",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version >= 1", name=op.f("ck_user_terms_acceptance_version_positive")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name=op.f("fk_user_terms_acceptance_user_id_user_account"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_user_terms_acceptance")),
    )
    op.create_table(
        "submission_upload",
        sa.Column("submission_id", sa.BigInteger(), nullable=False),
        sa.Column("upload_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["submission.id"],
            name=op.f("fk_submission_upload_submission_id_submission"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["upload_id"],
            ["upload.id"],
            name=op.f("fk_submission_upload_upload_id_upload"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("submission_id", "upload_id", name=op.f("pk_submission_upload")),
    )
    op.create_index("ix_submission_upload_upload_id", "submission_upload", ["upload_id"])

    op.add_column("submission", sa.Column("retry_of", sa.BigInteger(), nullable=True))
    op.add_column("submission", sa.Column("converts", sa.BigInteger(), nullable=True))
    op.add_column("submission", sa.Column("reduced_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "submission", sa.Column("stub", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    op.create_foreign_key(
        op.f("fk_submission_retry_of_submission"),
        "submission",
        "submission",
        ["retry_of"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        op.f("fk_submission_converts_submission"),
        "submission",
        "submission",
        ["converts"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "submission_log", sa.Column("related_submission_id", sa.BigInteger(), nullable=True)
    )
    op.create_foreign_key(
        op.f("fk_submission_log_related_submission_id_submission"),
        "submission_log",
        "submission",
        ["related_submission_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_constraint(op.f("ck_submission_log_event_allowed"), "submission_log", type_="check")
    op.create_check_constraint(
        op.f("ck_submission_log_event_allowed"), "submission_log", f"event IN ({NEW_EVENTS})"
    )

    op.add_column("upload", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "rate_limit_event",
        sa.Column("weight", sa.BigInteger(), server_default="1", nullable=False),
    )
