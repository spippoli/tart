"""The Discovery index: what search, filters, and orderings read (Discovery spec, Modules).

Condition, the chronological keys, and the date ranges come from the archive's domain
rules, which only Python implements; the index holds their results per Artwork, so that
one SQL query can filter, order, and count. It is derived data: `refresh` in
`tart.discovery.index` rebuilds a row from the public archive and nothing else writes
it. Visibility that changes outside a write (withdrawn, merged) is applied when
querying, from `record`.
"""

from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, Index, Table, Text
from sqlalchemy.dialects.postgresql import ARRAY, DATERANGE, TSVECTOR

from tart.db import Base

metadata = Base.metadata


def _artwork() -> ForeignKey:
    return ForeignKey("artwork.id", deferrable=True, initially="DEFERRED")


discovery_artwork = Table(
    "discovery_artwork",
    metadata,
    Column("artwork_id", BigInteger, _artwork(), primary_key=True),
    Column("condition", Text, nullable=False),
    Column("condition_group", Text, nullable=False),
    # The Creation event's range; null without a dated Creation event.
    Column("created_during", DATERANGE),
    # The chronological keys of the first and the last public Documentation item.
    Column("first_documented", DateTime),
    Column("last_documented", DateTime),
    # The approval of the Artwork's first Revision.
    Column("added_at", DateTime(timezone=True), nullable=False),
    # Any of `unknown`, `attributed`, `disputed`, as the public reads the Attributions.
    Column("attribution", ARRAY(Text), nullable=False),
    # The title as the public sees it, for the alphabetical order.
    Column("title", Text),
    Column("description", TSVECTOR),
)

discovery_documented = Table(
    "discovery_documented",
    metadata,
    Column("artwork_id", BigInteger, _artwork(), nullable=False),
    # One public Documentation item's Observed date range.
    Column("during", DATERANGE, nullable=False),
    Index("ix_discovery_documented_artwork_id", "artwork_id"),
    Index("ix_discovery_documented_during", "during", postgresql_using="gist"),
)

discovery_name = Table(
    "discovery_name",
    metadata,
    Column("artwork_id", BigInteger, _artwork(), nullable=False),
    # Lower-cased and unaccented, so that a trigram index serves the similarity search.
    Column("name", Text, nullable=False),
    # How much a match on this kind of name counts (Search, Matching and relevance).
    Column("weight", Float, nullable=False),
    Index("ix_discovery_name_artwork_id", "artwork_id"),
    Index(
        "ix_discovery_name_name",
        "name",
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    ),
)

archive_change = Table(
    "archive_change",
    metadata,
    # One row: a counter of the changes to the public archive, the ETag's seed.
    Column("id", BigInteger, primary_key=True),
    Column("counter", BigInteger, nullable=False),
)

__all__ = ["archive_change", "discovery_artwork", "discovery_documented", "discovery_name"]
