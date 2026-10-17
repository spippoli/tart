"""Merge, Duplicate retirement, and Unmerge through the HTTP API (contribution and moderation
spec, Merge, Duplicate retirement, Unmerge; criteria 26, 28, and 29). Every User and record is
fictional."""

import asyncio
import weakref
from collections.abc import Callable, Iterator
from dataclasses import replace
from typing import Any

import httpx2
import pytest
from archive_fixtures import PROVENANCE as SEEDED
from archive_fixtures import RULES, artwork, image, location, point
from auth_fixtures import Api, open_api

from tart.archive import Artist, ArtistKind, Create, New
from tart.archive_persistence import write_changeset
from tart.db import create_engine

PROVENANCE = replace(SEEDED, submission_id=0)
"""Seeded records belong to no Submission, whose ids start at 1."""


@pytest.fixture
def api(migrated_database: str) -> Iterator[Api]:
    with open_api(migrated_database) as started:
        yield started


_SESSIONS: weakref.WeakKeyDictionary[Any, dict[str, httpx2.Cookies]] = weakref.WeakKeyDictionary()


def _as(api: Api, email: str, *, moderator: bool = False) -> int:
    sessions = _SESSIONS.setdefault(api.client, {})
    api.client.cookies.clear()
    if email in sessions:
        api.client.cookies.update(sessions[email])
        number = api.client.get("/api/auth/session").json()["user"]["number"]
    else:
        number = api.sign_in(email)
        sessions[email] = httpx2.Cookies(api.client.cookies)
    if moderator:
        api.query(
            "INSERT INTO user_role (user_id, role) VALUES ($1, 'moderator') ON CONFLICT DO NOTHING",
            number,
        )
    return number


def _run(api: Api, work: Callable[[Any], Any]) -> Any:
    async def go() -> Any:
        engine = create_engine(api.dsn.replace("postgresql://", "postgresql+asyncpg://"))
        try:
            return await work(engine)
        finally:
            await engine.dispose()

    return asyncio.run(go())


def _seed(api: Api) -> dict[str, int]:
    """Two Locations on the same surface, each with an Artwork and one photograph."""

    async def work(engine: Any) -> dict[str, int]:
        ids = {}
        for name, position in (("x", point()), ("y", point(12.4824, 41.8956))):
            revisions = await write_changeset(
                engine,
                (
                    Create(New("l"), location(geometry=position)),
                    Create(New("a"), artwork(New("l"))),
                    Create(New("i"), image(New("a"))),
                ),
                PROVENANCE,
                RULES,
            )
            ids[f"location_{name}"], ids[f"artwork_{name}"], ids[f"item_{name}"] = [
                revision.record_id for revision in revisions
            ]
        return ids

    return _run(api, work)  # type: ignore[no-any-return]


def _decide(api: Api, submission_id: int, verdict: str) -> httpx2.Response:
    version = api.client.get(f"/api/contributions/{submission_id}").json()["version"]
    return api.client.post(
        f"/api/contributions/{submission_id}/decision",
        json={"verdict": verdict, "version": version},
    )


def _approved(api: Api, started: httpx2.Response) -> int:
    """Submit the draft the response describes, then approve it as a Moderator."""
    assert started.status_code == 201, started.text
    submission_id = started.json()["id"]
    submitted = api.client.post(
        f"/api/contributions/{submission_id}/submit", json={"accept_terms": True}
    )
    assert submitted.status_code == 200, submitted.text
    _as(api, "gus@example.org", moderator=True)
    approved = _decide(api, submission_id, "approve")
    assert approved.status_code == 200, approved.text
    _as(api, "ada@example.org")
    return submission_id


def test_starting_a_merge_needs_a_signed_in_user(api: Api) -> None:
    api.client.cookies.clear()

    response = api.client.post("/api/contributions/merge", json={"source_id": 1, "into_id": 2})

    assert response.status_code == 401


# Acceptance criterion 26.
def test_a_merge_is_proposed_reviewed_and_approved_through_the_api(api: Api) -> None:
    ids = _seed(api)
    _as(api, "ada@example.org")

    started = api.client.post(
        "/api/contributions/merge",
        json={"source_id": ids["location_x"], "into_id": ids["location_y"]},
    )

    assert started.status_code == 201
    draft = started.json()
    assert (draft["intent"], draft["target_id"], len(draft["base_revisions"])) == (
        "merge",
        ids["location_x"],
        2,
    )
    review = api.client.get(f"/api/contributions/{draft['id']}/merge")
    assert review.status_code == 200
    assert [(r["id"], r["kind"]) for r in review.json()["references"]] == [
        (ids["artwork_x"], "artwork")
    ]
    assert review.json()["source"]["id"] == ids["location_x"]

    _approved(api, started)

    assert (
        api.client.get(f"/api/archive/locations/{ids['location_x']}", follow_redirects=False)
        .headers["location"]
        .endswith(f"/locations/{ids['location_y']}")
    )
    moved = api.client.get(f"/api/archive/artworks/{ids['artwork_x']}").json()
    assert moved["where"]["location"]["id"] == ids["location_y"]
    revisions = api.client.get(f"/api/archive/locations/{ids['location_x']}/revisions")
    assert revisions.status_code == 200
    assert revisions.json()["merged_into"]["id"] == ids["location_y"]
    survivor = api.client.get(f"/api/archive/locations/{ids['location_y']}/revisions").json()
    merged = survivor["revisions"][0]["changes"][0]
    assert (merged["op"], merged["record"]["id"]) == ("merge", ids["location_x"])


def test_only_the_submitter_and_moderators_read_a_merge_review(api: Api) -> None:
    ids = _seed(api)
    _as(api, "ada@example.org")
    draft = api.client.post(
        "/api/contributions/merge",
        json={"source_id": ids["location_x"], "into_id": ids["location_y"]},
    ).json()["id"]

    _as(api, "ivo@example.org")
    stranger = api.client.get(f"/api/contributions/{draft}/merge")
    _as(api, "gus@example.org", moderator=True)
    moderator = api.client.get(f"/api/contributions/{draft}/merge")

    assert stranger.status_code == 404
    assert moderator.status_code == 200


def test_a_merge_of_records_of_two_kinds_is_refused_with_a_stable_code(api: Api) -> None:
    ids = _seed(api)
    _as(api, "ada@example.org")

    response = api.client.post(
        "/api/contributions/merge",
        json={"source_id": ids["location_x"], "into_id": ids["artwork_y"]},
    )

    assert response.status_code == 422
    assert response.json() == {"code": "moderation.merge_kind_mismatch"}


# Acceptance criteria 28 and 29.
def test_a_retirement_and_its_unmerge_go_through_the_api(api: Api) -> None:
    ids = _seed(api)
    _as(api, "ada@example.org")

    # Both photographs document the first Artwork: two items on one surface.
    async def second_photograph(engine: Any) -> int:
        revisions = await write_changeset(
            engine,
            (Create(New("i"), image(ids["artwork_x"], file="originals/second.jpg")),),
            PROVENANCE,
            RULES,
        )
        return revisions[0].record_id

    duplicate = _run(api, second_photograph)

    retire = api.client.post(
        "/api/contributions/merge", json={"source_id": duplicate, "into_id": ids["item_x"]}
    )
    assert retire.json()["intent"] == "retirement"
    _approved(api, retire)
    gone = api.client.get(f"/api/archive/documents/{duplicate}", follow_redirects=False)
    assert gone.status_code == 301

    restore = api.client.post("/api/contributions/unmerge", json={"source_id": duplicate})
    assert restore.json()["intent"] == "unmerge"
    _approved(api, restore)

    assert (
        api.client.get(f"/api/archive/documents/{duplicate}", follow_redirects=False).status_code
        == 200
    )


def test_the_candidates_of_a_merge_are_the_nearby_records_of_the_same_kind(api: Api) -> None:
    ids = _seed(api)
    _as(api, "ada@example.org")

    found = api.client.get(
        "/api/contributions/merge-candidates", params={"source_id": ids["location_x"]}
    )

    assert found.status_code == 200
    assert [(each["id"], each["kind"]) for each in found.json()["items"]] == [
        (ids["location_y"], "location")
    ]
    api.client.cookies.clear()
    assert (
        api.client.get(
            "/api/contributions/merge-candidates", params={"source_id": ids["location_x"]}
        ).status_code
        == 401
    )


# Acceptance criterion 28.
def test_a_retirement_of_items_on_different_locations_is_refused_at_once_with_a_code(
    api: Api,
) -> None:
    ids = _seed(api)
    _as(api, "ada@example.org")

    response = api.client.post(
        "/api/contributions/merge",
        json={"source_id": ids["item_x"], "into_id": ids["item_y"]},
    )

    assert response.status_code == 422
    assert response.json() == {"code": "duplicate_retirement.different_locations"}


def test_the_review_of_an_artist_merge_lists_the_aliases_to_add_and_the_choices(api: Api) -> None:
    async def work(engine: Any) -> list[int]:
        revisions = await write_changeset(
            engine,
            (
                Create(
                    New("x"),
                    Artist(name="Fictional Hand", kind=ArtistKind.INDIVIDUAL, aliases=("FH",)),
                ),
                Create(
                    New("y"),
                    Artist(name="Fictional Brush", kind=ArtistKind.INDIVIDUAL, aliases=("FB",)),
                ),
            ),
            PROVENANCE,
            RULES,
        )
        return [revision.record_id for revision in revisions]

    x, y = _run(api, work)
    _as(api, "ada@example.org")
    draft = api.client.post("/api/contributions/merge", json={"source_id": x, "into_id": y}).json()

    review = api.client.get(f"/api/contributions/{draft['id']}/merge").json()

    assert [(e["item"], e["origin"]) for e in review["items"] if e["collection"] == "aliases"] == [
        ("Fictional Hand", "source"),
        ("FH", "source"),
        ("FB", "into"),
    ]
    assert [(d["name"], d["source"], d["into"]) for d in review["fields"]] == [
        ("name", "Fictional Hand", "Fictional Brush")
    ]
    assert (review["intent"], review["contradictions"], review["references"]) == ("merge", [], [])
    assert (review["source"]["id"], review["into"]["id"]) == (x, y)
