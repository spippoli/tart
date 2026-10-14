"""Create the Discovery index.

Revision ID: 7d3e9b1f4a62
Revises: 5c2d8a7e1b34
Create Date: 2026-10-14 15:00:00.000000

Forward only (ADR 0020): add no reverse function.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7d3e9b1f4a62"
down_revision: str | Sequence[str] | None = "5c2d8a7e1b34"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _artwork_link(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["artwork_id"],
        ["artwork.id"],
        name=op.f(f"fk_{table}_artwork_id_artwork"),
        initially="DEFERRED",
        deferrable=True,
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table(
        "discovery_artwork",
        sa.Column("artwork_id", sa.BigInteger(), nullable=False),
        sa.Column("condition", sa.Text(), nullable=False),
        sa.Column("condition_group", sa.Text(), nullable=False),
        sa.Column("created_during", postgresql.DATERANGE(), nullable=True),
        sa.Column("first_documented", sa.DateTime(), nullable=True),
        sa.Column("last_documented", sa.DateTime(), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attribution", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("description", postgresql.TSVECTOR(), nullable=True),
        _artwork_link("discovery_artwork"),
        sa.PrimaryKeyConstraint("artwork_id", name=op.f("pk_discovery_artwork")),
    )
    op.create_table(
        "discovery_documented",
        sa.Column("artwork_id", sa.BigInteger(), nullable=False),
        sa.Column("during", postgresql.DATERANGE(), nullable=False),
        _artwork_link("discovery_documented"),
    )
    op.create_index(
        "ix_discovery_documented_artwork_id", "discovery_documented", ["artwork_id"], unique=False
    )
    op.create_index(
        "ix_discovery_documented_during",
        "discovery_documented",
        ["during"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_table(
        "discovery_name",
        sa.Column("artwork_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        _artwork_link("discovery_name"),
    )
    op.create_index("ix_discovery_name_artwork_id", "discovery_name", ["artwork_id"], unique=False)
    op.create_index(
        "ix_discovery_name_name",
        "discovery_name",
        ["name"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )
    archive_change = op.create_table(
        "archive_change",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("counter", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_archive_change")),
    )
    op.bulk_insert(archive_change, [{"id": 1, "counter": 0}])
