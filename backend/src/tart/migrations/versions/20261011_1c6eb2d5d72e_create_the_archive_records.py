"""Create the archive records: the eight record kinds, their collections, and Revisions.

Revision ID: 1c6eb2d5d72e
Revises: f3d81374dc84
Create Date: 2026-10-11 20:57:59.062854

Forward only (ADR 0020): add no reverse function.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision: str = "1c6eb2d5d72e"
down_revision: str | Sequence[str] | None = "f3d81374dc84"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "record",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('artwork', 'location', 'site', 'area', 'series', 'artist', 'source', "
            "'documentation_item')",
            name=op.f("ck_record_kind_allowed"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_record")),
    )
    op.create_geospatial_table(
        "area",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "geometry",
            Geometry(
                geometry_type="POLYGON",
                srid=4326,
                dimension=2,
                spatial_index=False,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                nullable=False,
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["id"],
            ["record.id"],
            name=op.f("fk_area_id_record"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_area")),
    )
    op.create_geospatial_index(
        "ix_area_geometry",
        "area",
        ["geometry"],
        unique=False,
        postgresql_using="gist",
        postgresql_ops={},
    )
    op.create_table(
        "artist",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("biography", sa.Text(), nullable=True),
        sa.Column("period", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint(
            "kind IN ('individual', 'collective')", name=op.f("ck_artist_kind_allowed")
        ),
        sa.ForeignKeyConstraint(
            ["id"],
            ["record.id"],
            name=op.f("fk_artist_id_record"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_artist")),
    )
    op.create_table(
        "revision",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("record_id", sa.BigInteger(), nullable=False),
        sa.Column("submission_id", sa.BigInteger(), nullable=False),
        sa.Column("submitter_id", sa.BigInteger(), nullable=False),
        sa.Column("moderator_id", sa.BigInteger(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("changes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["record_id"],
            ["record.id"],
            name=op.f("fk_revision_record_id_record"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_revision")),
    )
    op.create_index("ix_revision_record_id", "revision", ["record_id"], unique=False)
    op.create_table(
        "series",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["id"],
            ["record.id"],
            name=op.f("fk_series_id_record"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_series")),
    )
    op.create_table(
        "site",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["id"],
            ["record.id"],
            name=op.f("fk_site_id_record"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_site")),
    )
    op.create_table(
        "source",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("publication", sa.Text(), nullable=True),
        sa.Column("date", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("language", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["id"],
            ["record.id"],
            name=op.f("fk_source_id_record"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source")),
    )
    op.create_table(
        "artist_alias",
        sa.Column("artist_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["artist_id"],
            ["artist.id"],
            name=op.f("fk_artist_alias_artist_id_artist"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.PrimaryKeyConstraint("artist_id", "name", name=op.f("pk_artist_alias")),
    )
    op.create_table(
        "artist_area",
        sa.Column("artist_id", sa.BigInteger(), nullable=False),
        sa.Column("area_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["area_id"],
            ["area.id"],
            name=op.f("fk_artist_area_area_id_area"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.ForeignKeyConstraint(
            ["artist_id"],
            ["artist.id"],
            name=op.f("fk_artist_area_artist_id_artist"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.PrimaryKeyConstraint("artist_id", "area_id", name=op.f("pk_artist_area")),
    )
    op.create_table(
        "crew_membership",
        sa.Column("member_id", sa.BigInteger(), nullable=False),
        sa.Column("collective_id", sa.BigInteger(), nullable=False),
        sa.Column("period", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "member_id <> collective_id", name=op.f("ck_crew_membership_not_own_member")
        ),
        sa.ForeignKeyConstraint(
            ["collective_id"],
            ["artist.id"],
            name=op.f("fk_crew_membership_collective_id_artist"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.ForeignKeyConstraint(
            ["member_id"],
            ["artist.id"],
            name=op.f("fk_crew_membership_member_id_artist"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.PrimaryKeyConstraint("member_id", "collective_id", name=op.f("pk_crew_membership")),
    )
    op.create_index(
        "ix_crew_membership_collective_id", "crew_membership", ["collective_id"], unique=False
    )
    op.create_geospatial_table(
        "location",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column(
            "geometry",
            Geometry(
                srid=4326,
                dimension=2,
                spatial_index=False,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                nullable=False,
            ),
            nullable=False,
        ),
        sa.Column("approximate", sa.Boolean(), nullable=False),
        sa.Column("uncertainty_radius", sa.Integer(), nullable=True),
        sa.Column("surface_type", sa.Text(), nullable=False),
        sa.Column("site_id", sa.BigInteger(), nullable=True),
        sa.Column("place_description", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "uncertainty_radius IS NULL OR (approximate AND uncertainty_radius > 0 "
            "AND GeometryType(geometry) = 'POINT')",
            name=op.f("ck_location_radius_on_approximate_point"),
        ),
        sa.CheckConstraint(
            "char_length(place_description) <= 200",
            name=op.f("ck_location_place_description_length"),
        ),
        sa.ForeignKeyConstraint(
            ["id"],
            ["record.id"],
            name=op.f("fk_location_id_record"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["site.id"],
            name=op.f("fk_location_site_id_site"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_location")),
    )
    op.create_geospatial_index(
        "ix_location_geometry",
        "location",
        ["geometry"],
        unique=False,
        postgresql_using="gist",
        postgresql_ops={},
    )
    op.create_index("ix_location_site_id", "location", ["site_id"], unique=False)
    op.create_table(
        "record_source",
        sa.Column("record_id", sa.BigInteger(), nullable=False),
        sa.Column("source_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["record_id"],
            ["record.id"],
            name=op.f("fk_record_source_record_id_record"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["source.id"],
            name=op.f("fk_record_source_source_id_source"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.PrimaryKeyConstraint("record_id", "source_id", name=op.f("pk_record_source")),
    )
    op.create_table(
        "artwork",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("location_id", sa.BigInteger(), nullable=False),
        sa.Column("expression_types", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["id"],
            ["record.id"],
            name=op.f("fk_artwork_id_record"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["location.id"],
            name=op.f("fk_artwork_location_id_location"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_artwork")),
    )
    op.create_index("ix_artwork_location_id", "artwork", ["location_id"], unique=False)
    op.create_table(
        "documentation_item",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("medium", sa.Text(), nullable=False),
        sa.Column("observed_date", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("location_id", sa.BigInteger(), nullable=True),
        sa.Column("file", sa.Text(), nullable=True),
        sa.Column("licence", sa.Text(), nullable=True),
        sa.Column("creator_credit", sa.Text(), nullable=True),
        sa.Column("rights_basis", sa.Text(), nullable=True),
        sa.Column("origin_url", sa.Text(), nullable=True),
        sa.Column("alt_text", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("language", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "medium IN ('image', 'pdf', 'text', 'link')",
            name=op.f("ck_documentation_item_medium_allowed"),
        ),
        sa.CheckConstraint(
            "rights_basis IN ('own_work', 'third_party')",
            name=op.f("ck_documentation_item_rights_basis_allowed"),
        ),
        sa.CheckConstraint(
            "char_length(alt_text) <= 250", name=op.f("ck_documentation_item_alt_text_length")
        ),
        sa.ForeignKeyConstraint(
            ["id"],
            ["record.id"],
            name=op.f("fk_documentation_item_id_record"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["location.id"],
            name=op.f("fk_documentation_item_location_id_location"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documentation_item")),
    )
    op.create_table(
        "artwork_series",
        sa.Column("artwork_id", sa.BigInteger(), nullable=False),
        sa.Column("series_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["artwork_id"],
            ["artwork.id"],
            name=op.f("fk_artwork_series_artwork_id_artwork"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.ForeignKeyConstraint(
            ["series_id"],
            ["series.id"],
            name=op.f("fk_artwork_series_series_id_series"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.PrimaryKeyConstraint("artwork_id", "series_id", name=op.f("pk_artwork_series")),
    )
    op.create_index("ix_artwork_series_series_id", "artwork_series", ["series_id"], unique=False)
    op.create_table(
        "attribution",
        sa.Column("artwork_id", sa.BigInteger(), nullable=False),
        sa.Column("artist_id", sa.BigInteger(), nullable=False),
        sa.Column("certainty", sa.Text(), nullable=False),
        sa.Column("alias", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "certainty IN ('confirmed', 'probable', 'disputed')",
            name=op.f("ck_attribution_certainty_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["artist_id", "alias"],
            ["artist_alias.artist_id", "artist_alias.name"],
            name="fk_attribution_alias_artist_alias",
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.ForeignKeyConstraint(
            ["artist_id"],
            ["artist.id"],
            name=op.f("fk_attribution_artist_id_artist"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.ForeignKeyConstraint(
            ["artwork_id"],
            ["artwork.id"],
            name=op.f("fk_attribution_artwork_id_artwork"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.PrimaryKeyConstraint("artwork_id", "artist_id", name=op.f("pk_attribution")),
    )
    op.create_index("ix_attribution_artist_id", "attribution", ["artist_id"], unique=False)
    op.create_table(
        "documentation_item_artwork",
        sa.Column("item_id", sa.BigInteger(), nullable=False),
        sa.Column("artwork_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["artwork_id"],
            ["artwork.id"],
            name=op.f("fk_documentation_item_artwork_artwork_id_artwork"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["documentation_item.id"],
            name=op.f("fk_documentation_item_artwork_item_id_documentation_item"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.PrimaryKeyConstraint(
            "item_id", "artwork_id", name=op.f("pk_documentation_item_artwork")
        ),
    )
    op.create_index(
        "ix_documentation_item_artwork_artwork_id",
        "documentation_item_artwork",
        ["artwork_id"],
        unique=False,
    )
    op.create_table(
        "attribution_citation",
        sa.Column("artwork_id", sa.BigInteger(), nullable=False),
        sa.Column("artist_id", sa.BigInteger(), nullable=False),
        sa.Column("cited_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["artwork_id", "artist_id"],
            ["attribution.artwork_id", "attribution.artist_id"],
            name="fk_attribution_citation_attribution",
            ondelete="CASCADE",
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.ForeignKeyConstraint(
            ["cited_id"],
            ["record.id"],
            name=op.f("fk_attribution_citation_cited_id_record"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.PrimaryKeyConstraint(
            "artwork_id", "artist_id", "cited_id", name=op.f("pk_attribution_citation")
        ),
    )
