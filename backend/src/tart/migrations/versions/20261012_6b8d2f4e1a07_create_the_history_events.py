"""Create the History events.

Revision ID: 6b8d2f4e1a07
Revises: 3f6a1d9b8e25
Create Date: 2026-10-12 23:00:00.000000

Forward only (ADR 0020): add no reverse function.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "6b8d2f4e1a07"
down_revision: str | Sequence[str] | None = "3f6a1d9b8e25"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.schema.CreateSequence(sa.Sequence("history_event_id_seq")))
    op.create_table(
        "history_event",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("artwork_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("observed_date", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("condition", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("covering_artwork_id", sa.BigInteger(), nullable=True),
        sa.CheckConstraint(
            "type IN ('created', 'condition_recorded', 'deteriorated', 'damaged', "
            "'modified', 'covered', 'removed', 'destroyed', 'attribution_changed')",
            name=op.f("ck_history_event_type_allowed"),
        ),
        sa.CheckConstraint(
            "condition IN ('intact', 'deteriorated', 'damaged', 'modified', 'covered', "
            "'removed', 'destroyed', 'missing', 'unknown')",
            name=op.f("ck_history_event_condition_allowed"),
        ),
        sa.CheckConstraint(
            "(type = 'condition_recorded') = (condition IS NOT NULL)",
            name=op.f("ck_history_event_condition_on_condition_recorded"),
        ),
        sa.CheckConstraint(
            "covering_artwork_id IS NULL OR type = 'covered'",
            name=op.f("ck_history_event_covering_on_covered"),
        ),
        sa.ForeignKeyConstraint(
            ["artwork_id"],
            ["artwork.id"],
            name=op.f("fk_history_event_artwork_id_artwork"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.ForeignKeyConstraint(
            ["covering_artwork_id"],
            ["artwork.id"],
            name=op.f("fk_history_event_covering_artwork_id_artwork"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_history_event")),
    )
    op.create_index("ix_history_event_artwork_id", "history_event", ["artwork_id"], unique=False)
    op.create_table(
        "history_event_citation",
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("cited_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["cited_id"],
            ["record.id"],
            name=op.f("fk_history_event_citation_cited_id_record"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["history_event.id"],
            name=op.f("fk_history_event_citation_event_id_history_event"),
            ondelete="CASCADE",
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.PrimaryKeyConstraint("event_id", "cited_id", name=op.f("pk_history_event_citation")),
    )
