"""Contribution and moderation spec, Other editors: Submissions on every record kind, Sites
and Series created from fields, new Areas, Location geometry edits, and the refused edits
(acceptance criteria 45 to 50). Every record and User is fictional."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from archive_fixtures import RULES as ARCHIVE_RULES
from archive_fixtures import artwork, image, location, point, square
from auth_fixtures import Api, open_api
from moderation_fixtures import (
    ARTWORK,
    IMAGE,
    LOCATION,
    NOW,
    RULES,
    refusal,
    run,
    snapshot,
    user,
    write,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncConnection

from tart.archive import (
    AddItem,
    Area,
    Artist,
    ArtistKind,
    Attribution,
    Certainty,
    Create,
    CrewMembership,
    HistoryEventType,
    Kind,
    New,
    RemoveItem,
    Series,
    SetField,
    Site,
    Source,
)
from tart.archive_persistence import PostgresArchiveStore
from tart.archive_persistence import tables as t
from tart.archive_read import Reader, Viewer
from tart.moderation import Status
from tart.moderation_persistence import contribution, service, store


async def start_edit(
    connection: AsyncConnection, submitter: int, record_id: int, kind: Kind
) -> int:
    draft = await contribution.start(connection, submitter, kind, record_id, NOW, expiry_days=7)
    return draft.id


async def submit_edit(
    connection: AsyncConnection, submitter: int, record_id: int, kind: Kind, *operations: Any
) -> int:
    """An edit Submission of the record, submitted through the service."""
    draft = await start_edit(connection, submitter, record_id, kind)
    await service.submit(connection, draft, submitter, snapshot(*operations), NOW, ARCHIVE_RULES)
    return draft


async def approve(connection: AsyncConnection, submission_id: int, moderator: int) -> None:
    await service.approve(connection, submission_id, moderator, 1, RULES, ARCHIVE_RULES, NOW)


async def artwork_on_location(connection: AsyncConnection) -> tuple[int, int, int]:
    """A stored Location, an Artwork on it, and the image documenting that Artwork."""
    location_id, artwork_id, item_id = await write(
        connection,
        Create(LOCATION, location()),
        Create(ARTWORK, artwork(LOCATION)),
        Create(IMAGE, image(ARTWORK)),
    )
    return location_id, artwork_id, item_id


# Acceptance criterion 45.
def test_criterion_45_a_create_submission_on_a_site_series_source_or_item_is_refused(
    migrated_database: str,
) -> None:
    for kind in (Kind.SITE, Kind.SERIES, Kind.SOURCE, Kind.DOCUMENTATION_ITEM):

        async def starting(connection: AsyncConnection, kind: Kind = kind) -> object:
            submitter = await user(connection, kind.value.replace("_", ""))
            return await contribution.start(connection, submitter, kind, None, NOW, expiry_days=7)

        assert refusal(migrated_database, starting) == "moderation.target_not_creatable"

    async def submitting(connection: AsyncConnection) -> object:
        """A draft stored as the creation of a Site is refused when it is submitted too."""
        submitter = await user(connection, "ada")
        draft = await store.create_draft(connection, submitter, Kind.SITE, NOW)
        return await service.submit(
            connection,
            draft.id,
            submitter,
            snapshot(Create(New("site"), Site("Fictional hall"))),
            NOW,
            ARCHIVE_RULES,
        )

    assert refusal(migrated_database, submitting) == "moderation.target_not_creatable"


# Acceptance criterion 45.
def test_criterion_45_edit_submissions_on_each_of_them_are_accepted(migrated_database: str) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter = await user(connection, "ada")
        _, artwork_id, item_id = await artwork_on_location(connection)
        site_id, series_id, source_id = await write(
            connection,
            Create(New("site"), Site("Fictional hall")),
            Create(New("series"), Series("Fictional cats")),
            Create(New("source"), Source("A fictional zine")),
        )
        edits = [
            (Kind.SITE, site_id, SetField(site_id, "description", "A fictional wall.")),
            (Kind.SERIES, series_id, SetField(series_id, "name", "Fictional dogs")),
            (Kind.SOURCE, source_id, SetField(source_id, "author", "A. Fictional")),
            (Kind.DOCUMENTATION_ITEM, item_id, SetField(item_id, "alt_text", "A cat on a wall.")),
            (Kind.ARTWORK, artwork_id, SetField(artwork_id, "title", "A fictional cat")),
        ]
        for kind, record_id, operation in edits:
            submission_id = await submit_edit(connection, submitter, record_id, kind, operation)
            loaded = await store.load(connection, submission_id)
            assert loaded is not None and loaded.status is Status.SUBMITTED

    run(migrated_database, work)


# Acceptance criterion 46.
def test_criterion_46_a_site_created_from_a_locations_field_has_it_as_its_only_member(
    migrated_database: str,
) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter = await user(connection, "ada")
        moderator = await user(connection, "gus", moderator=True)
        location_id = (await write(connection, Create(LOCATION, location())))[0]
        site = New("site")
        submission_id = await submit_edit(
            connection,
            submitter,
            location_id,
            Kind.LOCATION,
            Create(site, Site("Fictional legal wall")),
            SetField(location_id, "site", site),
        )

        await approve(connection, submission_id, moderator)

        stored = await PostgresArchiveStore(connection).get(location_id)
        site_id = stored.site  # type: ignore[union-attr]
        assert isinstance(site_id, int)
        view = await Reader(connection, Viewer()).view(Kind.SITE, site_id)
        assert [each.id for each in view.locations] == [location_id]  # type: ignore[union-attr]
        assert view.name == "Fictional legal wall"

    run(migrated_database, work)


# Acceptance criterion 46.
def test_criterion_46_a_series_created_from_an_artworks_field_has_it_as_its_only_member(
    migrated_database: str,
) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter = await user(connection, "ada")
        moderator = await user(connection, "gus", moderator=True)
        _, artwork_id, _ = await artwork_on_location(connection)
        series = New("series")
        submission_id = await submit_edit(
            connection,
            submitter,
            artwork_id,
            Kind.ARTWORK,
            Create(series, Series("Fictional cats")),
            AddItem(artwork_id, "series", series),
        )

        await approve(connection, submission_id, moderator)

        stored = await PostgresArchiveStore(connection).get(artwork_id)
        (series_id,) = stored.series  # type: ignore[union-attr]
        view = await Reader(connection, Viewer()).view(Kind.SERIES, series_id)
        assert [each.id for each in view.artworks] == [artwork_id]  # type: ignore[union-attr]

    run(migrated_database, work)


# Acceptance criterion 46.
def test_criterion_46_a_site_or_series_edit_cannot_change_membership(
    migrated_database: str,
) -> None:
    async def setup(connection: AsyncConnection) -> tuple[int, int, int]:
        location_id = (await write(connection, Create(LOCATION, location())))[0]
        site_id, series_id = await write(
            connection,
            Create(New("site"), Site("Fictional hall")),
            Create(New("series"), Series("Fictional cats")),
        )
        return location_id, site_id, series_id

    location_id, site_id, series_id = run(migrated_database, setup)
    attempts = [
        (Kind.SITE, site_id, SetField(site_id, "locations", [location_id])),
        (Kind.SITE, site_id, AddItem(site_id, "locations", location_id)),
        (Kind.SERIES, series_id, SetField(series_id, "artworks", [1])),
        (Kind.SERIES, series_id, AddItem(series_id, "artworks", 1)),
    ]
    for number, (kind, record_id, operation) in enumerate(attempts):

        async def submitting(
            connection: AsyncConnection,
            number: int = number,
            kind: Kind = kind,
            record_id: int = record_id,
            operation: Any = operation,
        ) -> object:
            submitter = await user(connection, f"ada{number}")
            return await submit_edit(connection, submitter, record_id, kind, operation)

        assert refusal(migrated_database, submitting) == "moderation.malformed_content"


# Acceptance criterion 47.
def test_criterion_47_an_area_that_is_not_a_polygon_or_leaves_the_boundary_is_refused(
    migrated_database: str,
) -> None:
    two_vertices = {
        "type": "Polygon",
        "coordinates": [[[12.47, 41.88], [12.48, 41.89], [12.47, 41.88]]],
    }
    bow_tie = {
        "type": "Polygon",
        "coordinates": [
            [[12.47, 41.88], [12.49, 41.90], [12.49, 41.88], [12.47, 41.90], [12.47, 41.88]]
        ],
    }
    outside = square(12.30, 41.88, 12.50, 41.90).to_geojson()
    cases = [
        (two_vertices, "geometry.invalid"),
        (bow_tie, "geometry.self_intersecting"),
        (outside, "area.outside_boundary"),
    ]
    for number, (geometry, code) in enumerate(cases):

        async def submitting(
            connection: AsyncConnection, number: int = number, geometry: Any = geometry
        ) -> object:
            submitter = await user(connection, f"ada{number}")
            draft = await store.create_draft(connection, submitter, Kind.AREA, NOW)
            area = {"name": "Fictional rione", "geometry": geometry}
            return await service.submit(
                connection,
                draft.id,
                submitter,
                {"operations": [{"op": "create", "ref": "area", "kind": "area", "record": area}]},
                NOW,
                ARCHIVE_RULES,
            )

        assert refusal(migrated_database, submitting) == code


# Acceptance criterion 47.
def test_criterion_47_an_overlapping_area_is_accepted(migrated_database: str) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter = await user(connection, "ada")
        await write(
            connection,
            Create(New("old"), Area("Fictional rione", square(12.47, 41.88, 12.49, 41.90))),
        )
        draft = await store.create_draft(connection, submitter, Kind.AREA, NOW)
        await service.submit(
            connection,
            draft.id,
            submitter,
            snapshot(
                Create(New("area"), Area("Fictional ambit", square(12.48, 41.89, 12.50, 41.91)))
            ),
            NOW,
            ARCHIVE_RULES,
        )
        loaded = await store.load(connection, draft.id)
        assert loaded is not None and loaded.status is Status.SUBMITTED

    run(migrated_database, work)


# Acceptance criterion 48.
def test_criterion_48_a_geometry_edit_creates_no_history_event_on_approval(
    migrated_database: str,
) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter = await user(connection, "ada")
        moderator = await user(connection, "gus", moderator=True)
        location_id, artwork_id, _ = await artwork_on_location(connection)
        events = select(func.count()).select_from(t.history_event)
        before = await connection.scalar(events)
        submission_id = await submit_edit(
            connection,
            submitter,
            location_id,
            Kind.LOCATION,
            SetField(location_id, "geometry", point(12.4825, 41.8957)),
        )

        await approve(connection, submission_id, moderator)

        stored = await PostgresArchiveStore(connection).get(location_id)
        assert stored.geometry == point(12.4825, 41.8957)  # type: ignore[union-attr]
        assert await connection.scalar(events) == before
        kept = await PostgresArchiveStore(connection).get(artwork_id)
        assert [each.type for each in kept.history_events] == [  # type: ignore[union-attr]
            HistoryEventType.CONDITION_RECORDED
        ]

    run(migrated_database, work)


@pytest.fixture
def api(migrated_database: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Api]:
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path / "storage"))
    with open_api(migrated_database) as started:
        yield started


# Acceptance criterion 48 (the number of Artworks the edit shows comes from the API).
def test_criterion_48_the_edit_source_of_a_location_counts_its_artworks(
    api: Api, migrated_database: str
) -> None:
    async def setup(connection: AsyncConnection) -> int:
        location_id, *_ = await write(
            connection,
            Create(LOCATION, location()),
            Create(ARTWORK, artwork(LOCATION)),
            Create(New("second"), artwork(LOCATION)),
        )
        return location_id

    location_id = run(migrated_database, setup)
    api.sign_in("ada@example.org")
    started = api.client.post(
        "/api/contributions", json={"target_kind": "location", "target_id": location_id}
    )
    assert started.status_code == 201, started.text

    target = api.client.get(f"/api/contributions/{started.json()['id']}/target")

    assert target.status_code == 200, target.text
    body = target.json()
    assert (body["kind"], body["id"], body["artwork_count"]) == ("location", location_id, 2)
    assert body["record"]["surface_type"] == "building_wall"
    assert body["record"]["geometry"]["type"] == "Point"


def test_the_edit_source_is_for_the_submitter_of_an_edit_only(
    api: Api, migrated_database: str
) -> None:
    async def setup(connection: AsyncConnection) -> int:
        return (await write(connection, Create(LOCATION, location())))[0]

    location_id = run(migrated_database, setup)
    api.sign_in("ada@example.org")
    edit = api.client.post(
        "/api/contributions", json={"target_kind": "location", "target_id": location_id}
    ).json()["id"]
    new = api.client.post("/api/contributions", json={"target_kind": "artwork"}).json()["id"]

    assert api.client.get(f"/api/contributions/{new}/target").status_code == 404
    api.client.cookies.clear()
    assert api.client.get(f"/api/contributions/{edit}/target").status_code == 401
    api.sign_in("mallory@example.org")
    assert api.client.get(f"/api/contributions/{edit}/target").status_code == 404


# Acceptance criterion 49.
def test_criterion_49_an_item_edit_of_a_file_field_is_refused(migrated_database: str) -> None:
    changes = {
        "medium": "pdf",
        "file": "originals/other.jpg",
        "licence": "CC0-1.0",
        "creator_credit": "Someone else",
        "rights_basis": "third_party",
        "origin_url": "https://example.org/fictional",
    }

    async def setup(connection: AsyncConnection) -> int:
        return (await artwork_on_location(connection))[2]

    item_id = run(migrated_database, setup)
    for number, (name, value) in enumerate(changes.items()):

        async def submitting(
            connection: AsyncConnection, number: int = number, name: str = name, value: str = value
        ) -> object:
            submitter = await user(connection, f"ada{number}")
            draft = await start_edit(connection, submitter, item_id, Kind.DOCUMENTATION_ITEM)
            return await service.submit(
                connection,
                draft,
                submitter,
                {"operations": [{"op": "set", "target": item_id, "field": name, "value": value}]},
                NOW,
                ARCHIVE_RULES,
            )

        assert refusal(migrated_database, submitting) == f"documentation_item.{name}_immutable"


# Acceptance criterion 49.
def test_criterion_49_the_correctable_fields_of_an_item_are_accepted(
    migrated_database: str,
) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter = await user(connection, "ada")
        item_id = (await artwork_on_location(connection))[2]
        await submit_edit(
            connection,
            submitter,
            item_id,
            Kind.DOCUMENTATION_ITEM,
            SetField(item_id, "alt_text", "A fictional cat stencil, seen from the street."),
            SetField(item_id, "observed_date", image(ARTWORK).observed_date),
        )

    run(migrated_database, work)


# Acceptance criterion 50.
def test_criterion_50_removing_an_alias_an_attribution_names_fails_with_a_stable_code(
    migrated_database: str,
) -> None:
    async def setup(connection: AsyncConnection) -> int:
        (artist_id,) = await write(
            connection,
            Create(
                New("artist"), Artist("Fictional hand", ArtistKind.INDIVIDUAL, aliases=("Mano",))
            ),
        )
        await write(
            connection,
            Create(LOCATION, location()),
            Create(
                ARTWORK,
                artwork(
                    LOCATION,
                    attributions=(Attribution(artist_id, Certainty.PROBABLE, alias="Mano"),),
                ),
            ),
        )
        return artist_id

    artist_id = run(migrated_database, setup)

    async def submitting(connection: AsyncConnection) -> object:
        submitter = await user(connection, "ivo")
        return await submit_edit(
            connection, submitter, artist_id, Kind.ARTIST, RemoveItem(artist_id, "aliases", "Mano")
        )

    assert refusal(migrated_database, submitting) == "artist.alias_in_use"


# Acceptance criterion 50.
def test_criterion_50_a_crew_membership_that_forms_a_cycle_fails_with_a_stable_code(
    migrated_database: str,
) -> None:
    async def setup(connection: AsyncConnection) -> tuple[int, int]:
        collective_id, member_id = await write(
            connection,
            Create(New("collective"), Artist("Fictional crew", ArtistKind.COLLECTIVE)),
            Create(
                New("member"),
                Artist(
                    "Fictional members",
                    ArtistKind.COLLECTIVE,
                    crew_memberships=(CrewMembership(New("collective")),),
                ),
            ),
        )
        return collective_id, member_id

    collective_id, member_id = run(migrated_database, setup)

    async def submitting(connection: AsyncConnection) -> object:
        submitter = await user(connection, "ivo")
        return await submit_edit(
            connection,
            submitter,
            collective_id,
            Kind.ARTIST,
            AddItem(collective_id, "crew_memberships", CrewMembership(member_id)),
        )

    assert refusal(migrated_database, submitting) == "crew_membership.cycle"
