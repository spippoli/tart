"""The tables of Submissions, rounds, the Submission log, and Moderation notes (PostgreSQL)."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    PrimaryKeyConstraint,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

from tart.archive.records import Kind
from tart.db import Base
from tart.moderation.model import ActorKind, Event, Status

metadata = Base.metadata


def _one_of(column: str, values: type) -> CheckConstraint:
    allowed = ", ".join(f"'{value.value}'" for value in values)  # type: ignore[attr-defined]
    return CheckConstraint(f"{column} IN ({allowed})", name=f"{column}_allowed")


submission = Table(
    "submission",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("submitter_id", BigInteger, ForeignKey("user_account.id"), nullable=False),
    Column("target_kind", Text, nullable=False),
    # An edit's target; a create has none. A Submission never outlives the record it edits.
    Column("target_id", BigInteger, ForeignKey("record.id")),
    Column("base_revisions", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("status", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    # The draft's content, or the Submitter's private copy while a decision is pending.
    Column("working_copy", JSONB),
    Column("last_autosave_at", DateTime(timezone=True)),
    Column("working_copy_discarded", Boolean, nullable=False, server_default=text("false")),
    _one_of("status", Status),
    _one_of("target_kind", Kind),
    Index("ix_submission_status", "status"),
    Index("ix_submission_submitter_id", "submitter_id"),
)

submission_round = Table(
    "submission_round",
    metadata,
    Column("submission_id", BigInteger, ForeignKey("submission.id", ondelete="CASCADE")),
    Column("number", Integer),
    Column("snapshot", JSONB),
    Column("submitted_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("submission_id", "number"),
    CheckConstraint("number >= 1", name="number_positive"),
)

submission_log = Table(
    "submission_log",
    metadata,
    Column("submission_id", BigInteger, ForeignKey("submission.id", ondelete="CASCADE")),
    Column("position", Integer),
    Column("event", Text, nullable=False),
    Column("actor_kind", Text, nullable=False),
    # The system has no User; a deleted User keeps the row as a Pseudonym.
    Column("actor_id", BigInteger, ForeignKey("user_account.id")),
    Column("at", DateTime(timezone=True), nullable=False),
    Column("round", Integer),
    Column("message", Text),
    Column("reason", Text),
    PrimaryKeyConstraint("submission_id", "position"),
    _one_of("event", Event),
    _one_of("actor_kind", ActorKind),
    CheckConstraint("(actor_kind = 'user') = (actor_id IS NOT NULL)", name="actor_complete"),
)

moderation_note = Table(
    "moderation_note",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column(
        "submission_id", BigInteger, ForeignKey("submission.id", ondelete="CASCADE"), nullable=False
    ),
    Column("author_id", BigInteger, ForeignKey("user_account.id"), nullable=False),
    Column("at", DateTime(timezone=True), nullable=False),
    Column("text", Text, nullable=False),
    Index("ix_moderation_note_submission_id", "submission_id"),
)
