"""The archive's tables (PostgreSQL + PostGIS).

Every record has a row in `record`, whose id is shared by all kinds and never
reused, plus a row in its kind's table. Collections live in their own tables with
a `position` that keeps their order. Links between records are deferred foreign
keys, so one transaction can create records that refer to each other.
"""

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from tart.archive.records import ArtistKind, Certainty, Kind, Medium, RightsBasis
from tart.db import Base

metadata = Base.metadata


def _link(target: str, **kwargs: object) -> ForeignKey:
    return ForeignKey(target, deferrable=True, initially="DEFERRED", **kwargs)  # type: ignore[arg-type]


def _record_id() -> Column[int]:
    return Column("id", BigInteger, _link("record.id"), primary_key=True)


def _one_of(column: str, values: type) -> CheckConstraint:
    allowed = ", ".join(f"'{value.value}'" for value in values)  # type: ignore[attr-defined]
    return CheckConstraint(f"{column} IN ({allowed})", name=f"{column}_allowed")


record = Table(
    "record",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("kind", Text, nullable=False),
    _one_of("kind", Kind),
)

site = Table(
    "site",
    metadata,
    _record_id(),
    Column("name", Text, nullable=False),
    Column("description", Text),
)

location = Table(
    "location",
    metadata,
    _record_id(),
    # The one geometry the archive holds for the surface, the public one.
    Column("geometry", Geometry(srid=4326, spatial_index=False), nullable=False),
    Column("approximate", Boolean, nullable=False),
    Column("uncertainty_radius", Integer),
    Column("surface_type", Text, nullable=False),
    Column("site_id", BigInteger, _link("site.id")),
    Column("place_description", Text),
    CheckConstraint(
        "uncertainty_radius IS NULL OR (approximate AND uncertainty_radius > 0 "
        "AND GeometryType(geometry) = 'POINT')",
        name="radius_on_approximate_point",
    ),
    CheckConstraint("char_length(place_description) <= 200", name="place_description_length"),
    Index("ix_location_geometry", "geometry", postgresql_using="gist"),
    Index("ix_location_site_id", "site_id"),
)

area = Table(
    "area",
    metadata,
    _record_id(),
    Column("name", Text, nullable=False),
    Column("description", Text),
    Column("geometry", Geometry("POLYGON", srid=4326, spatial_index=False), nullable=False),
    Index("ix_area_geometry", "geometry", postgresql_using="gist"),
)

series = Table(
    "series",
    metadata,
    _record_id(),
    Column("name", Text, nullable=False),
    Column("description", Text),
)

artwork = Table(
    "artwork",
    metadata,
    _record_id(),
    Column("location_id", BigInteger, _link("location.id"), nullable=False),
    Column("expression_types", ARRAY(Text), nullable=False),
    Column("title", Text),
    Column("description", Text),
    Index("ix_artwork_location_id", "location_id"),
)

artist = Table(
    "artist",
    metadata,
    _record_id(),
    Column("name", Text, nullable=False),
    Column("kind", Text, nullable=False),
    Column("biography", Text),
    Column("period", JSONB),
    _one_of("kind", ArtistKind),
)

source = Table(
    "source",
    metadata,
    _record_id(),
    Column("title", Text, nullable=False),
    Column("author", Text),
    Column("publication", Text),
    Column("date", JSONB),
    Column("url", Text),
    Column("note", Text),
    Column("language", Text),
)

documentation_item = Table(
    "documentation_item",
    metadata,
    _record_id(),
    Column("medium", Text, nullable=False),
    Column("observed_date", JSONB, nullable=False),
    Column("location_id", BigInteger, _link("location.id")),
    Column("file", Text),
    Column("licence", Text),
    Column("creator_credit", Text),
    Column("rights_basis", Text),
    Column("origin_url", Text),
    Column("alt_text", Text),
    Column("text", Text),
    Column("url", Text),
    Column("language", Text),
    _one_of("medium", Medium),
    _one_of("rights_basis", RightsBasis),
    CheckConstraint("char_length(alt_text) <= 250", name="alt_text_length"),
)

# Collections.

record_source = Table(
    "record_source",
    metadata,
    Column("record_id", BigInteger, _link("record.id"), primary_key=True),
    Column("source_id", BigInteger, _link("source.id"), primary_key=True),
    Column("position", Integer, nullable=False),
)

artwork_series = Table(
    "artwork_series",
    metadata,
    Column("artwork_id", BigInteger, _link("artwork.id"), primary_key=True),
    Column("series_id", BigInteger, _link("series.id"), primary_key=True),
    Column("position", Integer, nullable=False),
    Index("ix_artwork_series_series_id", "series_id"),
)

artist_alias = Table(
    "artist_alias",
    metadata,
    Column("artist_id", BigInteger, _link("artist.id"), primary_key=True),
    Column("name", Text, primary_key=True),
    Column("position", Integer, nullable=False),
)

artist_area = Table(
    "artist_area",
    metadata,
    Column("artist_id", BigInteger, _link("artist.id"), primary_key=True),
    Column("area_id", BigInteger, _link("area.id"), primary_key=True),
    Column("position", Integer, nullable=False),
)

crew_membership = Table(
    "crew_membership",
    metadata,
    # One Artist may hold several memberships in one collective, over distinct periods.
    Column("member_id", BigInteger, _link("artist.id"), primary_key=True),
    Column("collective_id", BigInteger, _link("artist.id"), nullable=False),
    Column("period", JSONB),
    Column("position", Integer, primary_key=True),
    CheckConstraint("member_id <> collective_id", name="not_own_member"),
    Index("ix_crew_membership_collective_id", "collective_id"),
)

attribution = Table(
    "attribution",
    metadata,
    Column("artwork_id", BigInteger, _link("artwork.id"), primary_key=True),
    Column("artist_id", BigInteger, _link("artist.id"), primary_key=True),
    Column("certainty", Text, nullable=False),
    Column("alias", Text),
    Column("note", Text),
    Column("position", Integer, nullable=False),
    _one_of("certainty", Certainty),
    ForeignKeyConstraint(
        ["artist_id", "alias"],
        ["artist_alias.artist_id", "artist_alias.name"],
        name="fk_attribution_alias_artist_alias",
        deferrable=True,
        initially="DEFERRED",
    ),
    Index("ix_attribution_artist_id", "artist_id"),
)

attribution_citation = Table(
    "attribution_citation",
    metadata,
    Column("artwork_id", BigInteger, primary_key=True),
    Column("artist_id", BigInteger, primary_key=True),
    Column("cited_id", BigInteger, _link("record.id"), primary_key=True),
    Column("position", Integer, nullable=False),
    ForeignKeyConstraint(
        ["artwork_id", "artist_id"],
        ["attribution.artwork_id", "attribution.artist_id"],
        name="fk_attribution_citation_attribution",
        ondelete="CASCADE",
        deferrable=True,
        initially="DEFERRED",
    ),
)

documentation_item_artwork = Table(
    "documentation_item_artwork",
    metadata,
    Column("item_id", BigInteger, _link("documentation_item.id"), primary_key=True),
    Column("artwork_id", BigInteger, _link("artwork.id"), primary_key=True),
    Column("position", Integer, nullable=False),
    Index("ix_documentation_item_artwork_artwork_id", "artwork_id"),
)

revision = Table(
    "revision",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("record_id", BigInteger, _link("record.id"), nullable=False),
    # The Submission and the Users are added by later tickets, with their foreign keys.
    Column("submission_id", BigInteger, nullable=False),
    Column("submitter_id", BigInteger, nullable=False),
    Column("moderator_id", BigInteger, nullable=False),
    Column("submitted_at", DateTime(timezone=True), nullable=False),
    Column("approved_at", DateTime(timezone=True), nullable=False),
    Column("changes", JSONB, nullable=False),
    Index("ix_revision_record_id", "record_id"),
)
