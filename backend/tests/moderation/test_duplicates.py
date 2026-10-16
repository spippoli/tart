"""Contribution and moderation spec, Duplicate detection: criteria 23, 24, and 25.

The rules are tested as pure functions, then through PostGIS and the API. Every name and
record here is fictional.
"""

from collections.abc import Iterator
from datetime import date
from typing import Any

import pytest
from archive_fixtures import IN_ROME, Archive, artwork, event, image, location, point, square
from auth_fixtures import Api, open_api
from moderation_fixtures import ARTWORK, IMAGE, LOCATION, NOW, run, snapshot, submitted, user
from sqlalchemy.ext.asyncio import AsyncConnection

from tart.archive import (
    Area,
    Artist,
    ArtistKind,
    Condition,
    Create,
    Geometry,
    GeometryKind,
    HistoryEventType,
    Kind,
    New,
    Precision,
    Qualifier,
    Series,
    Site,
    Source,
    UncertainDate,
)
from tart.moderation import Status
from tart.moderation.duplicates import (
    NAME_THRESHOLD,
    PROXIMITY_METRES,
    Match,
    NamedRecord,
    name_candidates,
    name_score,
    normalise_name,
    normalise_url,
    proximity_limit,
    within_proximity,
)
from tart.moderation_persistence import service, store
from tart.moderation_persistence.duplicates import nearby_pending_creates

LONGITUDE, LATITUDE = IN_ROME
DEGREE = 111_000
"""Metres in a degree of latitude, near enough for a test that stays clear of the boundary."""


def north(metres: float, longitude: float = LONGITUDE) -> Geometry:
    """A point this many metres north of the reference point."""
    return point(longitude, LATITUDE + metres / DEGREE)


# The proximity rule.


def test_the_proximity_distance_is_25_metres_plus_the_radius_of_each_side() -> None:
    assert PROXIMITY_METRES == 25
    assert proximity_limit(None, None) == 25
    assert proximity_limit(10, None) == 35
    assert proximity_limit(10, 5) == 40
    assert within_proximity(25, None, None)
    assert not within_proximity(25.01, None, None)
    assert within_proximity(40, 10, 5)
    assert not within_proximity(40.01, 10, 5)


# The name rule: normalisation, the threshold, and its fixture of name pairs.

MUST_YIELD = [
    ("Gatto Nero", "gatto nero"),
    ("Quadraro", "Quadrarò"),
    ("Ex Fabbrica", "Ex-Fabbrica"),
    ("Tevere Crew", "Tevere Crew!"),
    ("Collettivo Muro", "Collettivo Muri"),
    ("Biblioteca Comunale", "Biblioteca Comunal"),
    ("Via dei Fienili", "Via dei Fienili 2"),
]
MUST_NOT_YIELD = [
    ("Testaccio", "Trastevere"),
    ("Ostiense", "Ostia"),
    ("Pino", "Pina"),
    ("Serie del Gatto", "Serie del Cane"),
    ("Collettivo Muro Nord", "Collettivo Muro Sud"),
    ("Gatto Nero", "Il Gatto Nero"),
    ("Anna Rossi", "Rossi Anna"),
]


def _named(name: str, *aliases: str, kind: Kind = Kind.ARTIST, url: str | None = None):
    return NamedRecord(1, kind, name, aliases, url)


@pytest.mark.parametrize(("new", "existing"), MUST_YIELD)
def test_criterion_24_a_name_pair_that_must_yield_a_candidate(new: str, existing: str) -> None:
    assert name_score(new, existing) >= NAME_THRESHOLD
    assert [c.record.id for c in name_candidates(new, [_named(existing)])] == [1]


@pytest.mark.parametrize(("new", "existing"), MUST_NOT_YIELD)
def test_criterion_24_a_name_pair_that_must_not_yield_a_candidate(new: str, existing: str) -> None:
    assert name_score(new, existing) < NAME_THRESHOLD
    assert name_candidates(new, [_named(existing)]) == []


def test_the_threshold_is_90() -> None:
    assert NAME_THRESHOLD == 90


def test_names_are_compared_without_case_accents_or_punctuation() -> None:
    assert normalise_name("  Çà-Va,  L'Òrso! ") == "ca va l orso"


def test_criterion_24_an_alias_matches_and_the_best_match_of_a_record_wins() -> None:
    record = _named("Nome Registrato", "Gufo Notturno", "Gufo Notturna")

    (candidate,) = name_candidates("gufo notturno", [record])

    assert (candidate.match, candidate.matched, candidate.score) == (
        Match.ALIAS,
        "Gufo Notturno",
        100.0,
    )


def test_criterion_24_candidates_come_best_score_first() -> None:
    records = [
        NamedRecord(1, Kind.SITE, "Mercato Rionale Nord"),
        NamedRecord(2, Kind.SITE, "Mercato Rionale Nord!"),
        NamedRecord(3, Kind.SITE, "Mercato Rionale Nor"),
    ]

    found = name_candidates("Mercato Rionale Nord", records)

    assert [c.record.id for c in found] == [1, 2, 3]
    assert found[0].score >= found[1].score >= found[2].score


def test_criterion_24_a_source_with_the_same_normalised_url_is_a_candidate() -> None:
    record = _named("Titolo diverso", kind=Kind.SOURCE, url="https://www.Example.org/archivio/")

    (candidate,) = name_candidates(
        "Un altro titolo", [record], url="http://example.org/archivio#sezione"
    )

    assert candidate.match is Match.URL
    assert normalise_url("HTTPS://WWW.Example.org/a/b/") == "example.org/a/b"
    assert name_candidates("Un altro titolo", [record], url="https://example.org/altro") == []
    assert name_candidates("Un altro titolo", [record]) == []


# The proximity rule and the name rule through PostGIS and the API.

DESTROYED = event(
    HistoryEventType.DESTROYED,
    observed_date=UncertainDate(Precision.YEAR, Qualifier.EXACT, date(2025, 1, 1)),
)


@pytest.fixture
def archive(migrated_database: str) -> Archive:
    return Archive(migrated_database)


@pytest.fixture
def api(migrated_database: str) -> Iterator[Api]:
    with open_api(migrated_database) as started:
        started.sign_in("lettrice@example.org")
        yield started


def _place(archive: Archive, geometry: Geometry, *titles: str, **values: Any) -> tuple[int, ...]:
    """A Location with an Artwork per title, the last of them destroyed; returns the ids of
    the Location and then of its Artworks."""
    changeset: list[Any] = [Create(New("l"), location(geometry=geometry, **values))]
    for number, title in enumerate(titles):
        events = (
            (event(),) if number < len(titles) - 1 or len(titles) == 1 else (event(), DESTROYED)
        )
        changeset.append(
            Create(New(f"w{number}"), artwork(New("l"), title=title, history_events=events))
        )
    revisions = archive.write(*changeset)
    return tuple(r.record_id for r in revisions)


def _locations(api: Api, **body: Any):
    return api.client.post("/api/contribution/duplicates/locations", json=body)


def _ids(response) -> list[int]:
    return [c["location"]["id"] for c in response.json()["candidates"]]


def test_criterion_23_a_location_within_25_metres_is_listed_with_all_its_artworks(
    api: Api, archive: Archive
) -> None:
    here, present, gone = _place(archive, north(0), "Gatto sul portone", "Gufo sul muro")

    response = _locations(api, geometry=north(20).to_geojson())

    assert response.status_code == 200
    (candidate,) = response.json()["candidates"]
    assert candidate["location"]["id"] == here
    assert candidate["location"]["surface_type"] == "building_wall"
    assert candidate["location"]["geometry"]["type"] == "Point"
    assert 15 < candidate["distance"] < 25
    groups = {a["id"]: a["condition"]["group"] for a in candidate["artworks"]}
    assert groups == {present: "present", gone: "disappeared"}


def test_criterion_23_candidates_are_ordered_by_distance(api: Api, archive: Archive) -> None:
    far, *_ = _place(archive, north(22), "Lontano")
    near, *_ = _place(archive, north(8), "Vicino")
    middle, *_ = _place(archive, north(-15), "Nel mezzo")

    response = _locations(api, geometry=north(0).to_geojson())

    assert _ids(response) == [near, middle, far]
    distances = [c["distance"] for c in response.json()["candidates"]]
    assert distances == sorted(distances)


def test_criterion_23_the_25_metre_boundary(api: Api, archive: Archive) -> None:
    inside, *_ = _place(archive, north(24))
    _place(archive, north(-26))

    assert _ids(_locations(api, geometry=north(0).to_geojson())) == [inside]


def test_criterion_23_uncertainty_radii_widen_the_distance_on_both_sides(
    api: Api, archive: Archive
) -> None:
    stored_wide, *_ = _place(archive, north(-40), approximate=True, uncertainty_radius=20)
    asked_wide, *_ = _place(archive, north(60))
    asking = north(0).to_geojson()

    # 40 m is within 25 m plus the stored radius of 20 m; 60 m is not.
    assert _ids(_locations(api, geometry=asking)) == [stored_wide]
    # A radius on the asking side counts too: 25 m + 20 m + 20 m reaches 65 m.
    assert _ids(_locations(api, geometry=asking, uncertainty_radius=20)) == [stored_wide]
    assert _ids(_locations(api, geometry=asking, uncertainty_radius=40)) == [
        stored_wide,
        asked_wide,
    ]


def test_criterion_23_lines_and_polygons_are_compared_by_their_nearest_edge(
    api: Api, archive: Archive
) -> None:
    line = Geometry(
        GeometryKind.LINE, ((LONGITUDE - 0.001, LATITUDE), (LONGITUDE + 0.001, LATITUDE))
    )
    on_line, *_ = _place(archive, line)
    d = 20 / DEGREE
    box = square(LONGITUDE + 0.01, LATITUDE, LONGITUDE + 0.012, LATITUDE + 0.002)
    on_polygon, *_ = _place(archive, box)

    near_line = _locations(api, geometry=north(20).to_geojson())
    near_polygon = _locations(
        api, geometry=point(LONGITUDE + 0.01 - d * 1.3, LATITUDE + 0.001).to_geojson()
    )
    drawn_polygon = _locations(
        api,
        geometry=square(
            LONGITUDE - 0.0002, LATITUDE + 0.0002, LONGITUDE + 0.0002, LATITUDE + 0.0006
        ).to_geojson(),
    )

    assert _ids(near_line) == [on_line]
    assert _ids(near_polygon) == [on_polygon]
    assert _ids(drawn_polygon) == [on_line]


def test_criterion_23_choosing_an_existing_location_lists_it_and_its_neighbours(
    api: Api, archive: Archive
) -> None:
    chosen, *_ = _place(archive, north(0), "Scelto")
    neighbour, *_ = _place(archive, north(15), "Accanto")
    _place(archive, north(200), "Lontano")

    response = _locations(api, location_id=chosen)

    assert _ids(response) == [chosen, neighbour]
    assert response.json()["candidates"][0]["distance"] == 0


def test_criterion_23_a_withdrawn_or_merged_location_is_not_offered(
    api: Api, archive: Archive
) -> None:
    withdrawn, *_ = _place(archive, north(5))
    merged, *_ = _place(archive, north(6))
    kept, *_ = _place(archive, north(7))
    api.query("UPDATE record SET withdrawn_at = now() WHERE id = $1", withdrawn)
    api.query("UPDATE record SET merged_into = $1 WHERE id = $2", kept, merged)

    assert _ids(_locations(api, geometry=north(0).to_geojson())) == [kept]
    assert _locations(api, location_id=withdrawn).status_code == 404


def test_criterion_23_the_request_is_checked(api: Api) -> None:
    assert _locations(api).status_code == 422
    assert _locations(api, geometry=north(0).to_geojson(), location_id=1).status_code == 422
    assert _locations(api, location_id=999_999).json() == {"code": "record_not_found"}
    bad = _locations(api, geometry={"type": "Point", "coordinates": [500, 500]})
    assert (bad.status_code, bad.json()) == (422, {"code": "geometry_invalid"})


def test_the_duplicate_endpoints_need_a_signed_in_user(api: Api) -> None:
    api.client.post("/api/auth/sign-out")

    assert _locations(api, geometry=north(0).to_geojson()).status_code == 401
    names = api.client.post(
        "/api/contribution/duplicates/names", json={"kind": "artist", "name": "Gufo"}
    )
    assert names.status_code == 401


def _names(api: Api, kind: str, name: str, **body: Any):
    return api.client.post(
        "/api/contribution/duplicates/names", json={"kind": kind, "name": name, **body}
    )


def test_criterion_24_an_artist_name_or_alias_is_matched_without_blocking(
    api: Api, archive: Archive
) -> None:
    artist = archive.ids(
        archive.write(
            Create(
                New("a"),
                Artist(
                    name="Mano Anonima",
                    kind=ArtistKind.INDIVIDUAL,
                    aliases=("Orso Quadrarò", "Il Cacciatore"),
                ),
            )
        )
    )[0]

    by_name = _names(api, "artist", "mano anonima")
    by_alias = _names(api, "artist", "Orso Quadraro")
    unrelated = _names(api, "artist", "Gufo Notturno")

    assert by_name.status_code == by_alias.status_code == unrelated.status_code == 200
    (found,) = by_name.json()["candidates"]
    assert (found["record"]["id"], found["match"], found["score"]) == (artist, "name", 100.0)
    assert found["record"]["name"] == "Mano Anonima"
    (found,) = by_alias.json()["candidates"]
    assert (found["record"]["id"], found["match"], found["matched"]) == (
        artist,
        "alias",
        "Orso Quadrarò",
    )
    assert unrelated.json() == {"candidates": []}


def test_criterion_24_sites_series_and_areas_are_matched_by_name(
    api: Api, archive: Archive
) -> None:
    site = archive.ids(archive.write(Create(New("s"), Site(name="Ex Fabbrica del Ghiaccio"))))[0]
    series = archive.ids(archive.write(Create(New("s"), Series(name="Gatti dei Portoni"))))[0]
    area = archive.ids(
        archive.write(
            Create(
                New("a"),
                Area(name="Quartiere Fittizio", geometry=square(12.45, 41.88, 12.47, 41.9)),
            )
        )
    )[0]

    assert [
        c["record"]["id"]
        for c in _names(api, "site", "Ex-Fabbrica del ghiaccio").json()["candidates"]
    ] == [site]
    assert [
        c["record"]["id"] for c in _names(api, "series", "Gatti dei portoni").json()["candidates"]
    ] == [series]
    assert [
        c["record"]["id"] for c in _names(api, "area", "Quartiere fittizio").json()["candidates"]
    ] == [area]
    # Each kind is compared with its own kind only.
    assert _names(api, "series", "Ex Fabbrica del Ghiaccio").json() == {"candidates": []}


def test_criterion_24_a_source_matches_by_title_or_by_the_same_normalised_url(
    api: Api, archive: Archive
) -> None:
    source = archive.ids(
        archive.write(
            Create(
                New("s"),
                Source(title="Rassegna fittizia dei muri", url="https://www.example.org/rassegna/"),
            )
        )
    )[0]

    by_title = _names(api, "source", "Rassegna fittizia dei muri.")
    by_url = _names(api, "source", "Titolo del tutto diverso", url="http://example.org/rassegna")
    neither = _names(api, "source", "Titolo del tutto diverso", url="https://example.org/altro")

    assert [(c["record"]["id"], c["match"]) for c in by_title.json()["candidates"]] == [
        (source, "name")
    ]
    assert [(c["record"]["id"], c["match"]) for c in by_url.json()["candidates"]] == [
        (source, "url")
    ]
    assert neither.json() == {"candidates": []}


def test_criterion_24_a_withdrawn_record_is_not_offered(api: Api, archive: Archive) -> None:
    withdrawn = archive.ids(archive.write(Create(New("s"), Site(name="Sito ritirato"))))[0]
    api.query("UPDATE record SET withdrawn_at = now() WHERE id = $1", withdrawn)

    assert _names(api, "site", "Sito ritirato").json() == {"candidates": []}


def test_criterion_24_an_artwork_title_is_not_a_name_to_match(api: Api) -> None:
    assert _names(api, "artwork", "Gatto").status_code == 422


# Criterion 25: the queue flag.


def _new_location_snapshot(geometry: Geometry, **values: Any):
    return snapshot(
        Create(LOCATION, location(geometry=geometry, **values)),
        Create(ARTWORK, artwork(LOCATION, history_events=())),
        Create(IMAGE, image(ARTWORK)),
        condition=Condition.INTACT,
    )


def test_criterion_25_pending_creates_within_25_metres_of_each_other_are_flagged(
    migrated_database: str,
) -> None:
    async def work(connection: AsyncConnection) -> tuple[list[int], dict[int, tuple[int, ...]]]:
        ada = await user(connection, "ada")
        bea = await user(connection, "bea")
        cleo = await user(connection, "cleo")
        first = await submitted(connection, ada, _new_location_snapshot(north(0)))
        second = await submitted(connection, bea, _new_location_snapshot(north(20)))
        apart = await submitted(connection, cleo, _new_location_snapshot(north(200)))
        return [first, second, apart], await nearby_pending_creates(connection)

    (first, second, apart), flags = run(migrated_database, work)

    assert flags == {first: (second,), second: (first,)}
    assert apart not in flags


def test_criterion_25_the_boundary_and_the_uncertainty_radii_follow_the_proximity_rule(
    migrated_database: str,
) -> None:
    async def work(connection: AsyncConnection) -> tuple[list[int], dict, dict]:
        ada = await user(connection, "ada")
        bea = await user(connection, "bea")
        cleo = await user(connection, "cleo")
        first = await submitted(connection, ada, _new_location_snapshot(north(0)))
        second = await submitted(connection, bea, _new_location_snapshot(north(26)))
        outside = await nearby_pending_creates(connection)
        wide = await submitted(
            connection,
            cleo,
            _new_location_snapshot(north(40), approximate=True, uncertainty_radius=20),
        )
        return [first, second, wide], outside, await nearby_pending_creates(connection)

    (first, second, wide), outside, widened = run(migrated_database, work)

    assert outside == {}
    assert widened == {first: (wide,), second: (wide,), wide: (first, second)}


def test_criterion_25_only_submissions_awaiting_a_decision_that_create_a_location_count(
    migrated_database: str,
) -> None:
    async def work(connection: AsyncConnection) -> dict[int, tuple[int, ...]]:
        ada = await user(connection, "ada")
        bea = await user(connection, "bea")
        cleo = await user(connection, "cleo")
        await submitted(connection, ada, _new_location_snapshot(north(0)))
        retracted = await submitted(connection, bea, _new_location_snapshot(north(5)))
        await service.retract(connection, retracted, bea, NOW)
        # A draft is not pending.
        await store.create_draft(connection, cleo, Kind.ARTWORK, NOW)
        return await nearby_pending_creates(connection)

    assert run(migrated_database, work) == {}


def test_criterion_25_the_flag_leaves_the_status_alone(migrated_database: str) -> None:
    async def work(connection: AsyncConnection) -> Status:
        ada, bea = await user(connection, "ada"), await user(connection, "bea")
        first = await submitted(connection, ada, _new_location_snapshot(north(0)))
        await submitted(connection, bea, _new_location_snapshot(north(10)))
        await nearby_pending_creates(connection)
        loaded = await store.load(connection, first)
        assert loaded is not None
        return loaded.status

    assert run(migrated_database, work) is Status.SUBMITTED
