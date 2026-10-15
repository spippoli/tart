"""Create the Submissions, their rounds, the Submission log, and the Moderation notes.

Revision ID: 2a9c4e7b1d35
Revises: 7d3e9b1f4a62
Create Date: 2026-10-16 09:00:00.000000

Forward only (ADR 0020): add no reverse function.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "2a9c4e7b1d35"
down_revision: str | Sequence[str] | None = "7d3e9b1f4a62"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "submission",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("submitter_id", sa.BigInteger(), nullable=False),
        sa.Column("target_kind", sa.Text(), nullable=False),
        sa.Column("target_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "base_revisions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("working_copy", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_autosave_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "working_copy_discarded", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'submitted', 'changes_requested', 'approved', 'rejected', "
            "'retracted')",
            name=op.f("ck_submission_status_allowed"),
        ),
        sa.CheckConstraint(
            "target_kind IN ('artwork', 'location', 'site', 'area', 'series', 'artist', "
            "'source', 'documentation_item')",
            name=op.f("ck_submission_target_kind_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["submitter_id"],
            ["user_account.id"],
            name=op.f("fk_submission_submitter_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["target_id"], ["record.id"], name=op.f("fk_submission_target_id_record")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_submission")),
    )
    op.create_index("ix_submission_status", "submission", ["status"])
    op.create_index("ix_submission_submitter_id", "submission", ["submitter_id"])
    op.create_table(
        "submission_round",
        sa.Column("submission_id", sa.BigInteger(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("number >= 1", name=op.f("ck_submission_round_number_positive")),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["submission.id"],
            name=op.f("fk_submission_round_submission_id_submission"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("submission_id", "number", name=op.f("pk_submission_round")),
    )
    op.create_table(
        "submission_log",
        sa.Column("submission_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("event", sa.Text(), nullable=False),
        sa.Column("actor_kind", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.BigInteger(), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("round", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "event IN ('submitted', 'revised', 'resubmitted', 'approved', 'rejected', "
            "'changes_requested', 'retracted', 'expired')",
            name=op.f("ck_submission_log_event_allowed"),
        ),
        sa.CheckConstraint(
            "actor_kind IN ('user', 'system')", name=op.f("ck_submission_log_actor_kind_allowed")
        ),
        sa.CheckConstraint(
            "(actor_kind = 'user') = (actor_id IS NOT NULL)",
            name=op.f("ck_submission_log_actor_complete"),
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["user_account.id"], name=op.f("fk_submission_log_actor_id_user_account")
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["submission.id"],
            name=op.f("fk_submission_log_submission_id_submission"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("submission_id", "position", name=op.f("pk_submission_log")),
    )
    op.create_table(
        "moderation_note",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("submission_id", sa.BigInteger(), nullable=False),
        sa.Column("author_id", sa.BigInteger(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["user_account.id"],
            name=op.f("fk_moderation_note_author_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["submission.id"],
            name=op.f("fk_moderation_note_submission_id_submission"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_moderation_note")),
    )
    op.create_index("ix_moderation_note_submission_id", "moderation_note", ["submission_id"])
