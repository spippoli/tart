"""The archive write operation over PostgreSQL + PostGIS (archive-records spec, Modules and
Revisions). Every record here is fictional.
"""

import asyncio
from dataclasses import fields, replace
from datetime import UTC, date, datetime

import pytest
from archive_fixtures import (
    OBSERVED,
    PROVENANCE,
    Archive,
    artwork,
    image,
    location,
    point,
    square,
)
from conftest import VALID_CONFIG, fetch_value

from tart.archive import (
    AddItem,
    ArchiveRuleViolation,
    Area,
    Artist,
    ArtistKind,
    Artwork,
    Attribution,
    Certainty,
    ChangeItem,
    Create,
    CrewMembership,
    DocumentationItem,
    Geometry,
    GeometryKind,
    Kind,
    Location,
    Medium,
    New,
    Period,
    Precision,
    Qualifier,
    RemoveItem,
    Series,
    SetField,
    Site,
    Source,
    UncertainDate,
)
from tart.archive_persistence import PostgresArchiveStore
from tart.config import load_instance
from tart.config.database import check_database

LOCATION, ARTWORK, IMAGE = New("location"), New("artwork"), New("image")


@pytest.fixture
def archive(migrated_database: str) -> Archive:
    return Archive(migrated_database)


def _rejected(archive: Archive, *changeset: object) -> str:
    with pytest.raises(ArchiveRuleViolation) as raised:
        archive.write(*changeset)  # type: ignore[arg-type]
    return raised.value.code


def _new_artwork(archive: Archive, **values: object) -> tuple[int, int]:
    """A new Artwork on a new Location; returns their ids."""
    revisions = archive.write(
        Create(LOCATION, location()),
        Create(ARTWORK, artwork(LOCATION, **values)),
        Create(IMAGE, image(ARTWORK)),
    )
    location_id, artwork_id, _ = archive.ids(revisions)
    return artwork_id, location_id


def _dsn(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")


# Revisions.


def test_a_changeset_creates_its_records_with_one_revision_each(archive: Archive) -> None:
    revisions = archive.write(
        Create(LOCATION, location(place_description="Fictional shutter at no. 3")),
        Create(ARTWORK, artwork(LOCATION, title="Fictional cat")),
        Create(IMAGE, image(ARTWORK)),
    )

    assert [revision.kind for revision in revisions] == [
        Kind.LOCATION,
        Kind.ARTWORK,
        Kind.DOCUMENTATION_ITEM,
    ]
    location_id, artwork_id, image_id = archive.ids(revisions)
    assert archive.get(artwork_id) == artwork(location_id, title="Fictional cat")
    assert archive.get(image_id) == image(artwork_id)
    for revision in revisions:
        assert revision.provenance == PROVENANCE
        assert archive.read(lambda store, r=revision: store.revisions_of(r.record_id)) == (
            revision,
        )
    # The first Revision lists the initial values.
    assert revisions[1].changes == (
        {"op": "set", "field": "location", "old": None, "new": location_id},
        {"op": "set", "field": "expression_types", "old": None, "new": ["stencil"]},
        {"op": "set", "field": "title", "old": None, "new": "Fictional cat"},
    )


def test_an_edit_produces_one_revision_with_its_change_list(archive: Archive) -> None:
    artwork_id, _ = _new_artwork(archive, title="Fictional cat")
    later = replace(PROVENANCE, submission_id=7, approved_at=datetime(2026, 9, 10, tzinfo=UTC))

    revisions = archive.write(
        SetField(artwork_id, "title", "Fictional black cat"),
        SetField(artwork_id, "description", "A fictional description."),
        provenance=later,
    )

    assert len(revisions) == 1
    assert revisions[0].record_id == artwork_id
    assert revisions[0].provenance == later
    assert revisions[0].changes == (
        {"op": "set", "field": "title", "old": "Fictional cat", "new": "Fictional black cat"},
        {"op": "set", "field": "description", "old": None, "new": "A fictional description."},
    )
    assert len(archive.read(lambda store: store.revisions_of(artwork_id))) == 2


def test_a_record_left_unchanged_gets_no_revision(archive: Archive) -> None:
    artwork_id, _ = _new_artwork(archive, title="Fictional cat")

    assert archive.write(SetField(artwork_id, "title", "Fictional cat")) == ()


def test_a_failing_changeset_stores_nothing(archive: Archive, migrated_database: str) -> None:
    code = _rejected(
        archive,
        Create(LOCATION, location()),
        Create(ARTWORK, artwork(LOCATION)),
        Create(New("source"), Source("   ")),
    )

    assert code == "source.title_required"
    for table in ("record", "location", "artwork", "revision"):
        assert fetch_value(_dsn(migrated_database), f"SELECT count(*) FROM {table}") == 0


def test_the_write_is_one_transaction(
    archive: Archive, migrated_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []
    original = PostgresArchiveStore.add_revision

    async def fail_on_the_second(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(args)
        if len(calls) == 2:
            raise RuntimeError("the database went away")
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(PostgresArchiveStore, "add_revision", fail_on_the_second)

    with pytest.raises(RuntimeError):
        archive.write(Create(LOCATION, location()), Create(ARTWORK, artwork(LOCATION)))

    for table in ("record", "location", "artwork", "revision"):
        assert fetch_value(_dsn(migrated_database), f"SELECT count(*) FROM {table}") == 0


def test_records_refer_only_to_records_of_the_right_kind(archive: Archive) -> None:
    artwork_id, location_id = _new_artwork(archive)

    assert _rejected(archive, Create(ARTWORK, artwork(artwork_id))) == "changeset.invalid_reference"
    assert _rejected(archive, Create(ARTWORK, artwork(999))) == "changeset.invalid_reference"
    assert _rejected(archive, SetField(999, "title", "x")) == "changeset.unknown_record"
    assert _rejected(archive, Create(ARTWORK, artwork(New("nowhere")))) == (
        "changeset.unknown_new_record"
    )
    assert _rejected(archive, SetField(location_id, "colour", "red")) == "changeset.unknown_field"


# Criterion 4: no operation deletes an Artwork or a Location.


def test_criterion_4_removing_items_never_deletes_records(archive: Archive) -> None:
    artwork_id, location_id = _new_artwork(archive)
    series_id = archive.ids(
        archive.write(
            Create(New("series"), Series("Fictional cats")),
            AddItem(artwork_id, "series", New("series")),
        )
    )[0]

    archive.write(RemoveItem(artwork_id, "series", series_id))

    assert archive.get(series_id) == Series("Fictional cats")
    assert archive.get(artwork_id) == artwork(location_id)
    assert _rejected(archive, SetField(artwork_id, "location", None)) == (
        "artwork.location_required"
    )
    assert _rejected(archive, RemoveItem(artwork_id, "location", location_id)) == (
        "changeset.unknown_collection"
    )
    assert archive.get(location_id) == location()


# Criterion 7.


def test_criterion_7_a_confirmed_attribution_needs_a_citation(archive: Archive) -> None:
    artwork_id, _ = _new_artwork(archive)
    artist_id, source_id = archive.ids(
        archive.write(
            Create(New("artist"), Artist("Nebbia Finta (fictional)", ArtistKind.INDIVIDUAL)),
            Create(New("source"), Source("A fictional interview")),
        )
    )
    confirmed = Attribution(artist_id, Certainty.CONFIRMED)

    assert _rejected(archive, AddItem(artwork_id, "attributions", confirmed)) == (
        "attribution.confirmed_requires_citation"
    )
    archive.write(AddItem(artwork_id, "attributions", replace(confirmed, citations=(source_id,))))

    stored = archive.get(artwork_id)
    assert isinstance(stored, Artwork)
    assert stored.attributions == (replace(confirmed, citations=(source_id,)),)


def test_criterion_7_a_citation_created_in_the_same_changeset_counts(archive: Archive) -> None:
    artwork_id, _ = _new_artwork(archive)

    archive.write(
        Create(New("artist"), Artist("Nebbia Finta (fictional)", ArtistKind.INDIVIDUAL)),
        Create(New("source"), Source("A fictional interview")),
        AddItem(
            artwork_id,
            "attributions",
            Attribution(New("artist"), Certainty.CONFIRMED, citations=(New("source"),)),
        ),
    )


def test_an_attribution_names_only_an_alias_of_its_artist(archive: Archive) -> None:
    artwork_id, _ = _new_artwork(archive)
    artist_id = archive.ids(
        archive.write(
            Create(
                New("artist"),
                Artist("Nebbia Finta (fictional)", ArtistKind.INDIVIDUAL, aliases=("NF",)),
            )
        )
    )[0]

    assert _rejected(
        archive,
        AddItem(artwork_id, "attributions", Attribution(artist_id, Certainty.PROBABLE, "XX")),
    ) == ("attribution.alias_not_of_artist")
    archive.write(
        AddItem(artwork_id, "attributions", Attribution(artist_id, Certainty.PROBABLE, "NF"))
    )
    assert _rejected(archive, RemoveItem(artist_id, "aliases", "NF")) == "artist.alias_in_use"
    archive.write(
        ChangeItem(artwork_id, "attributions", Attribution(artist_id, Certainty.PROBABLE)),
        RemoveItem(artist_id, "aliases", "NF"),
    )


# Criterion 10.


def test_criterion_10_a_location_outside_the_boundary_is_rejected(archive: Archive) -> None:
    assert _rejected(archive, Create(LOCATION, location(geometry=point(13.0, 41.9)))) == (
        "location.outside_boundary"
    )


def test_criterion_10_moving_a_location_outside_the_boundary_is_rejected(
    archive: Archive,
) -> None:
    _, location_id = _new_artwork(archive)

    assert _rejected(archive, SetField(location_id, "geometry", point(12.0, 41.9))) == (
        "location.outside_boundary"
    )


def test_criterion_10_a_self_intersecting_polygon_is_rejected(archive: Archive) -> None:
    with pytest.raises(ArchiveRuleViolation) as raised:
        Geometry.from_geojson(
            {
                "type": "Polygon",
                "coordinates": [
                    [[12.48, 41.89], [12.49, 41.90], [12.49, 41.89], [12.48, 41.90], [12.48, 41.89]]
                ],
            }
        )

    assert raised.value.code == "geometry.self_intersecting"


# Criterion 11.


def test_criterion_11_an_uncertainty_radius_only_on_an_approximate_point(archive: Archive) -> None:
    location_id = archive.ids(
        archive.write(Create(LOCATION, location(approximate=True, uncertainty_radius=40)))
    )[0]

    assert archive.get(location_id) == location(approximate=True, uncertainty_radius=40)
    assert _rejected(archive, SetField(location_id, "approximate", False)) == (
        "location.radius_requires_approximate_point"
    )


# Criterion 12.


def test_criterion_12_an_image_of_artworks_on_two_locations_is_rejected(archive: Archive) -> None:
    first, _ = _new_artwork(archive)
    second, _ = _new_artwork(archive)

    assert _rejected(archive, Create(IMAGE, image(first, second))) == (
        "documentation_item.image_on_several_locations"
    )
    archive.write(
        Create(
            New("link"),
            DocumentationItem(
                Medium.LINK, image().observed_date, (first, second), url="https://example.org/a"
            ),
        )
    )


def test_criterion_12_moving_an_artwork_away_from_its_shared_image_is_rejected(
    archive: Archive,
) -> None:
    first, location_id = _new_artwork(archive)
    second = archive.ids(
        archive.write(
            Create(ARTWORK, artwork(location_id)),
            Create(IMAGE, image(first, ARTWORK)),
        )
    )[0]
    other_location = archive.ids(archive.write(Create(LOCATION, location())))[0]

    assert _rejected(archive, SetField(second, "location", other_location)) == (
        "documentation_item.image_on_several_locations"
    )


# Criterion 29.


def test_criterion_29_the_archive_stores_only_the_public_geometry(
    archive: Archive, migrated_database: str
) -> None:
    precise = point(12.4823456, 41.8955123)
    location_id = archive.ids(
        archive.write(Create(LOCATION, location(geometry=precise, approximate=True)))
    )[0]

    stored = archive.get(location_id)
    assert isinstance(stored, Location)
    assert stored.geometry == precise
    columns = fetch_value(
        _dsn(migrated_database),
        "SELECT string_agg(f_table_name || '.' || f_geometry_column, ',' ORDER BY f_table_name) "
        "FROM geometry_columns WHERE f_table_schema = 'public'",
    )
    assert columns == "area.geometry,location.geometry"


# Criterion 42.


def test_criterion_42_changing_the_location_creates_no_history_event(archive: Archive) -> None:
    artwork_id, former = _new_artwork(archive)
    corrected = archive.ids(archive.write(Create(LOCATION, location())))[0]

    revisions = archive.write(SetField(artwork_id, "location", corrected))

    assert [(revision.record_id, revision.changes) for revision in revisions] == [
        (artwork_id, ({"op": "set", "field": "location", "old": former, "new": corrected},))
    ]
    assert archive.read(lambda store: store.artworks_on_location(former)) == ()
    assert archive.read(lambda store: store.artworks_on_location(corrected)) == (artwork_id,)
    # The former Location stays, with no Artwork on it.
    assert archive.get(former) == location()


# Criterion 44.


def test_criterion_44_sites_areas_and_series_store_an_optional_description(
    archive: Archive,
) -> None:
    area = square(12.47, 41.88, 12.49, 41.90)
    records = [
        Site("Fictional hall of fame", "A fictional legal wall."),
        Site("Fictional yard"),
        Area("Fictional rione", area, "A fictional district."),
        Area("Fictional quarter", area),
        Series("Fictional cats", "A fictional series."),
        Series("Fictional dogs"),
    ]

    ids = archive.ids(
        archive.write(*(Create(New(str(i)), record) for i, record in enumerate(records)))
    )

    assert [archive.get(record_id) for record_id in ids] == records


# Criterion 47.


def test_criterion_47_an_artwork_can_belong_to_several_series(archive: Archive) -> None:
    artwork_id, location_id = _new_artwork(archive)

    first, second = archive.ids(
        archive.write(
            Create(New("cats"), Series("Fictional cats")),
            Create(New("walls"), Series("Fictional walls")),
            AddItem(artwork_id, "series", New("cats")),
            AddItem(artwork_id, "series", New("walls")),
        )
    )[:2]

    assert archive.get(artwork_id) == artwork(location_id, series=(first, second))


def test_criterion_47_a_collective_cannot_be_its_own_member(archive: Archive) -> None:
    crew = archive.ids(
        archive.write(Create(New("crew"), Artist("Fictional crew", ArtistKind.COLLECTIVE)))
    )[0]

    assert _rejected(archive, AddItem(crew, "crew_memberships", CrewMembership(crew))) == (
        "crew_membership.cycle"
    )


def test_criterion_47_a_crew_membership_cycle_through_a_chain_is_rejected(
    archive: Archive,
) -> None:
    a, b, c = archive.ids(
        archive.write(
            Create(New("a"), Artist("Fictional crew A", ArtistKind.COLLECTIVE)),
            Create(
                New("b"),
                Artist(
                    "Fictional crew B",
                    ArtistKind.COLLECTIVE,
                    crew_memberships=(CrewMembership(New("a")),),
                ),
            ),
            Create(
                New("c"),
                Artist(
                    "Fictional crew C",
                    ArtistKind.COLLECTIVE,
                    crew_memberships=(CrewMembership(New("b")),),
                ),
            ),
        )
    )

    assert _rejected(archive, AddItem(a, "crew_memberships", CrewMembership(c))) == (
        "crew_membership.cycle"
    )
    # Nesting without a cycle is fine.
    member = archive.ids(
        archive.write(
            Create(
                New("member"),
                Artist(
                    "Fictional writer",
                    ArtistKind.INDIVIDUAL,
                    crew_memberships=(CrewMembership(a), CrewMembership(c)),
                ),
            )
        )
    )[0]
    assert archive.read(lambda store: store.members_of(a)) == {b, member}


def _years(start: int, end: int | None = None) -> Period:
    return Period(
        start=UncertainDate(Precision.YEAR, Qualifier.EXACT, date(start, 1, 1)),
        end=UncertainDate(Precision.YEAR, Qualifier.EXACT, date(end, 1, 1)) if end else None,
    )


def test_criterion_60_an_artist_may_rejoin_a_collective_over_distinct_periods(
    archive: Archive,
) -> None:
    solo, crew = archive.ids(
        archive.write(
            Create(New("solo"), Artist("Fictional writer", ArtistKind.INDIVIDUAL)),
            Create(New("crew"), Artist("Fictional crew", ArtistKind.COLLECTIVE)),
        )
    )
    first, second = CrewMembership(crew, _years(2008, 2011)), CrewMembership(crew, _years(2015))

    archive.write(
        AddItem(solo, "crew_memberships", first), AddItem(solo, "crew_memberships", second)
    )

    stored = archive.get(solo)
    assert isinstance(stored, Artist)
    assert stored.crew_memberships == (first, second)
    archive.write(RemoveItem(solo, "crew_memberships", second.key))
    stored = archive.get(solo)
    assert isinstance(stored, Artist)
    assert stored.crew_memberships == (first,)


@pytest.mark.parametrize(
    "period",
    [
        _years(2010, 2012),  # overlaps 2008-2011
        _years(2011, 2013),  # equal keys at 2011
        _years(2005),  # open-ended from before
        None,  # no period overlaps every other membership
    ],
)
def test_criterion_60_overlapping_memberships_in_one_collective_are_rejected(
    archive: Archive, period: Period | None
) -> None:
    solo, crew = archive.ids(
        archive.write(
            Create(New("solo"), Artist("Fictional writer", ArtistKind.INDIVIDUAL)),
            Create(New("crew"), Artist("Fictional crew", ArtistKind.COLLECTIVE)),
        )
    )
    archive.write(AddItem(solo, "crew_memberships", CrewMembership(crew, _years(2008, 2011))))

    assert _rejected(archive, AddItem(solo, "crew_memberships", CrewMembership(crew, period))) == (
        "crew_membership.periods_overlap"
    )


def test_criterion_59_linking_documentation_gives_a_revision_to_the_item_only(
    archive: Archive,
) -> None:
    first, location_id = _new_artwork(archive)
    second = archive.ids(archive.write(Create(ARTWORK, artwork(location_id))))[0]

    created = archive.write(Create(IMAGE, image(first)))
    assert [revision.kind for revision in created] == [Kind.DOCUMENTATION_ITEM]
    item = created[0].record_id

    linked = archive.write(AddItem(item, "artworks", second))
    unlinked = archive.write(RemoveItem(item, "artworks", first))

    for revisions in (linked, unlinked):
        assert [revision.record_id for revision in revisions] == [item]
    assert [
        len(archive.read(lambda store, a=a: store.revisions_of(a))) for a in (first, second)
    ] == [1, 1]


def test_only_a_collective_has_members(archive: Archive) -> None:
    solo, crew = archive.ids(
        archive.write(
            Create(New("solo"), Artist("Fictional writer", ArtistKind.INDIVIDUAL)),
            Create(New("crew"), Artist("Fictional crew", ArtistKind.COLLECTIVE)),
        )
    )

    assert _rejected(archive, AddItem(crew, "crew_memberships", CrewMembership(solo))) == (
        "crew_membership.not_a_collective"
    )
    archive.write(AddItem(solo, "crew_memberships", CrewMembership(crew)))
    assert _rejected(archive, SetField(crew, "kind", ArtistKind.INDIVIDUAL)) == (
        "crew_membership.not_a_collective"
    )


# Area membership.


def test_area_membership_is_computed_from_geometry_including_overlaps(archive: Archive) -> None:
    location_id = archive.ids(archive.write(Create(LOCATION, location())))[0]
    inside, overlapping, elsewhere = archive.ids(
        archive.write(
            Create(New("1"), Area("Fictional rione", square(12.47, 41.88, 12.49, 41.90))),
            Create(New("2"), Area("Fictional ambit", square(12.48, 41.89, 12.50, 41.91))),
            Create(New("3"), Area("Fictional suburb", square(12.52, 41.92, 12.54, 41.94))),
        )
    )

    assert archive.read(lambda store: store.areas_of_location(location_id)) == (
        overlapping,
        inside,
    )
    # Redrawing an Area changes membership with nothing else to update.
    archive.write(SetField(elsewhere, "geometry", square(12.40, 41.85, 12.56, 41.95)))
    assert set(archive.read(lambda store: store.areas_of_location(location_id))) == {
        inside,
        overlapping,
        elsewhere,
    }


def test_a_line_location_belongs_to_every_area_it_touches(archive: Archive) -> None:
    line = Geometry(GeometryKind.LINE, ((12.475, 41.895), (12.485, 41.895)))
    location_id = archive.ids(archive.write(Create(LOCATION, location(geometry=line))))[0]
    west, east = archive.ids(
        archive.write(
            Create(New("west"), Area("Fictional west", square(12.47, 41.89, 12.48, 41.90))),
            Create(New("east"), Area("Fictional east", square(12.48, 41.89, 12.49, 41.90))),
        )
    )

    assert archive.read(lambda store: store.areas_of_location(location_id)) == (east, west)


# Every record kind round-trips.


def test_every_record_kind_reads_back_as_written(archive: Archive) -> None:
    period = Period(start=UncertainDate(Precision.DECADE, Qualifier.CIRCA, date(2010, 1, 1)))
    records = {
        "site": Site("Fictional hall of fame", sources=(New("source"),)),
        "location": location(site=New("site"), place_description="Fictional pier, river side"),
        "artwork": artwork(
            New("location"),
            title="Fictional cat",
            expression_types=("stencil", "mural"),
            attributions=(
                Attribution(
                    New("crew"),
                    Certainty.CONFIRMED,
                    "FC",
                    "A fictional note.",
                    (New("source"), New("image")),
                ),
                Attribution(New("solo"), Certainty.DISPUTED),
            ),
            series=(New("series"),),
            sources=(New("source"),),
        ),
        "image": image(New("artwork")),
        "series": Series("Fictional cats"),
        "area": Area("Fictional rione", square(12.47, 41.88, 12.49, 41.90)),
        "crew": Artist(
            "Fictional crew", ArtistKind.COLLECTIVE, aliases=("FC", "F.C."), period=period
        ),
        "solo": Artist(
            "Fictional writer",
            ArtistKind.INDIVIDUAL,
            biography="A fictional biography.",
            areas=(New("area"),),
            crew_memberships=(CrewMembership(New("crew"), period),),
            sources=(New("source"),),
        ),
        "source": Source(
            "A fictional interview",
            author="Fictional author",
            publication="Fictional magazine",
            date=OBSERVED,
            url="https://example.org/interview",
            note="p. 12",
            language="en",
        ),
    }

    revisions = archive.write(*(Create(New(key), record) for key, record in records.items()))

    ids = dict(zip(records, archive.ids(revisions), strict=True))
    for key, record in records.items():
        assert archive.get(ids[key]) == _with_ids(record, ids)


def _with_ids(value: object, ids: dict[str, int]) -> object:
    """The value with every `New` replaced by the id the write gave it."""
    if isinstance(value, New):
        return ids[value.key]
    if isinstance(value, tuple):
        return tuple(_with_ids(item, ids) for item in value)
    if isinstance(
        value, (Artwork, Location, Site, Artist, DocumentationItem, Attribution, CrewMembership)
    ):
        return replace(
            value, **{f.name: _with_ids(getattr(value, f.name), ids) for f in fields(value)}
        )
    return value


def test_the_vocabulary_keys_in_use_are_checked_against_the_configuration(
    archive: Archive,
) -> None:
    _new_artwork(archive)
    instance = load_instance(VALID_CONFIG)
    without_stencil = {
        **instance.vocabularies,
        "expression_types": tuple(
            entry for entry in instance.vocabularies["expression_types"] if entry.key != "stencil"
        ),
        "surface_types": (),
    }

    issues = asyncio.run(check_database(replace(instance, vocabularies=without_stencil)))

    assert [(issue.file, "artwork" in issue.message) for issue in issues] == [
        ("vocabularies/expression_types.toml", True),
        ("vocabularies/surface_types.toml", False),
    ]
