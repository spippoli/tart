"""Contribution and moderation spec, Queue, Submission page, Moderator identity and Moderation
notes: criteria 33, 34, 37, 43, and 52 (and the queue's flags of 25), through the HTTP API.

Every User, record, and file is fictional.
"""

import json
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx2
import pytest
from archive_fixtures import (
    IN_ROME,
    Archive,
    artwork,
    event,
    image,
    location,
    point,
    square,
)
from archive_fixtures import RULES as ARCHIVE_RULES
from auth_fixtures import Api, instance_with, open_api
from moderation_fixtures import (
    ARTWORK,
    IMAGE,
    LOCATION,
    NOW,
    new_artwork_snapshot,
    run,
    snapshot,
    submitted,
    user,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from tart.archive import (
    Area,
    Condition,
    Create,
    Geometry,
    Kind,
    New,
    Precision,
    Qualifier,
    SetField,
    UncertainDate,
)
from tart.archive_persistence import PostgresArchiveStore
from tart.moderation_persistence import service

LONGITUDE, LATITUDE = IN_ROME
DEGREE = 111_000
DAY = timedelta(days=1)


def north(metres: float) -> Geometry:
    return point(LONGITUDE, LATITUDE + metres / DEGREE)


@pytest.fixture
def archive(migrated_database: str) -> Archive:
    return Archive(migrated_database)


@pytest.fixture
def api(migrated_database: str) -> Iterator[Api]:
    with open_api(migrated_database) as started:
        yield started


class Callers:
    """Sign in once per person and switch between them without asking for another code."""

    def __init__(self, api: Api) -> None:
        self.api = api
        self.cookies: dict[str, httpx2.Cookies] = {}
        self.numbers: dict[str, int] = {}

    def be(self, name: str, *, moderator: bool = False) -> int:
        self.api.client.cookies.clear()
        if name not in self.cookies:
            number = self.api.sign_in(f"{name}@example.org", name.title())
            if moderator:
                self.api.query(
                    "INSERT INTO user_role (user_id, role) VALUES ($1, 'moderator')", number
                )
            self.cookies[name] = httpx2.Cookies(self.api.client.cookies)
            self.numbers[name] = number
        else:
            self.api.client.cookies.update(self.cookies[name])
        return self.numbers[name]

    def anonymous(self) -> None:
        self.api.client.cookies.clear()


@pytest.fixture
def callers(api: Api) -> Callers:
    return Callers(api)


def _new_artwork_at(geometry: Geometry, **values: Any):
    return snapshot(
        Create(LOCATION, location(geometry=geometry, **values)),
        Create(ARTWORK, artwork(LOCATION, history_events=())),
        Create(IMAGE, image(ARTWORK)),
        condition=Condition.INTACT,
    )


def _queue(api: Api, **query: Any) -> list[dict[str, Any]]:
    response = api.client.get("/api/moderation/queue", params=query)
    assert response.status_code == 200, response.text
    return response.json()["items"]


def _ids(items: list[dict[str, Any]]) -> list[int]:
    return [item["id"] for item in items]


# Criterion 34: orders and filters.


def test_criterion_34_the_queue_is_oldest_first_by_default_and_offers_two_more_orders(
    api: Api, callers: Callers, migrated_database: str
) -> None:
    gus = callers.be("gus", moderator=True)

    async def work(connection: AsyncConnection) -> list[int]:
        ada = await user(connection, "ada")
        first = await submitted(connection, ada, at=NOW + DAY)
        second = await submitted(connection, ada, at=NOW + 2 * DAY)
        third = await submitted(connection, ada, at=NOW + 3 * DAY)
        # A revision opens a new round but the Submission keeps its place by first submission.
        await service.submit(
            connection, first, ada, new_artwork_snapshot(), NOW + 5 * DAY, ARCHIVE_RULES
        )
        return [first, second, third]

    first, second, third = run(migrated_database, work)
    assert gus

    assert _ids(_queue(api)) == [first, second, third]
    assert _ids(_queue(api, sort="oldest")) == [first, second, third]
    assert _ids(_queue(api, sort="newest")) == [third, second, first]
    assert _ids(_queue(api, sort="resubmitted")) == [first, third, second]
    assert api.client.get("/api/moderation/queue", params={"sort": "popular"}).status_code == 422


def test_criterion_34_nothing_in_the_queue_ranks_by_popularity(
    api: Api, callers: Callers, migrated_database: str
) -> None:
    callers.be("gus", moderator=True)

    async def work(connection: AsyncConnection) -> None:
        await submitted(connection, await user(connection, "ada"))

    run(migrated_database, work)

    (item,) = _queue(api)

    assert set(item) == {
        "id",
        "target_kind",
        "intent",
        "target_id",
        "labels",
        "submitter",
        "own",
        "first_submitted_at",
        "latest_round_at",
        "rounds",
        "outdated",
        "overlapping",
        "nearby_creates",
    }
    assert set(item["submitter"]) == {"number", "display_name"}


def test_criterion_34_the_queue_lists_what_awaits_a_decision_and_filters_by_label_kind_submitter(
    api: Api, callers: Callers, migrated_database: str, archive: Archive
) -> None:
    callers.be("gus", moderator=True)
    _, artwork_id = archive.ids(
        archive.write(
            Create(New("l"), location()), Create(New("w"), artwork(New("l"), title="Gatto"))
        )
    )
    base = _revision(archive, artwork_id)

    async def work(connection: AsyncConnection) -> dict[str, Any]:
        ada, bea = await user(connection, "ada"), await user(connection, "bea")
        creation = await submitted(connection, ada)
        documentation = await submitted(
            connection,
            bea,
            snapshot(Create(New("i"), image(artwork_id, file="originals/due.jpg"))),
            target_id=artwork_id,
            base_revisions=(base,),
        )
        retracted = await submitted(connection, ada)
        await service.retract(connection, retracted, ada, NOW)
        return {"creation": creation, "documentation": documentation, "ada": ada, "bea": bea}

    found = run(migrated_database, work)
    creation, documentation = found["creation"], found["documentation"]

    assert sorted(_ids(_queue(api))) == [creation, documentation]
    assert _ids(_queue(api, target_kind="artwork")) == [creation, documentation]
    assert _ids(_queue(api, target_kind="location")) == []
    assert _ids(_queue(api, label="adds_documentation")) == [creation, documentation]
    assert _ids(_queue(api, label="changes_attribution")) == []
    assert _ids(_queue(api, submitter=found["bea"])) == [documentation]
    assert _ids(_queue(api, submitter=found["ada"])) == [creation]


def test_criterion_34_the_area_filter_keeps_the_submissions_about_a_place_inside_it(
    api: Api, callers: Callers, migrated_database: str, archive: Archive
) -> None:
    callers.be("gus", moderator=True)
    (area_id,) = archive.ids(
        archive.write(
            Create(
                New("a"),
                Area(name="Quartiere fittizio", geometry=square(12.48, 41.89, 12.49, 41.90)),
            )
        )
    )

    async def work(connection: AsyncConnection) -> tuple[int, int]:
        ada = await user(connection, "ada")
        inside = await submitted(connection, ada, _new_artwork_at(point(12.485, 41.895)))
        outside = await submitted(connection, ada, _new_artwork_at(point(12.45, 41.87)))
        return inside, outside

    inside, outside = run(migrated_database, work)

    assert sorted(_ids(_queue(api))) == [inside, outside]
    assert _ids(_queue(api, area=area_id)) == [inside]


def test_criterion_34_the_outdated_filter_and_the_flags(
    api: Api, callers: Callers, migrated_database: str, archive: Archive
) -> None:
    callers.be("gus", moderator=True)
    _, artwork_id = archive.ids(
        archive.write(
            Create(New("l"), location()), Create(New("w"), artwork(New("l"), title="Gatto"))
        )
    )
    base = _revision(archive, artwork_id)

    async def work(connection: AsyncConnection) -> tuple[int, int, int, int, int]:
        ada, bea = await user(connection, "ada"), await user(connection, "bea")
        stale = await submitted(
            connection,
            ada,
            snapshot(SetField(artwork_id, "title", "Gatto sul portone")),
            target_id=artwork_id,
            base_revisions=(base,),
        )
        other = await submitted(
            connection,
            bea,
            snapshot(SetField(artwork_id, "description", "Un gatto fittizio.")),
            target_id=artwork_id,
            base_revisions=(base,),
        )
        near_a = await submitted(connection, ada, _new_artwork_at(north(0)))
        near_b = await submitted(connection, bea, _new_artwork_at(north(10)))
        far = await submitted(connection, bea, _new_artwork_at(north(400)))
        return stale, other, near_a, near_b, far

    stale, other, near_a, near_b, far = run(migrated_database, work)
    # Someone else's approved change to the same field makes the first one Outdated.
    archive.write(SetField(artwork_id, "title", "Gatto sul muro"))

    items = {item["id"]: item for item in _queue(api)}

    assert items[stale]["outdated"] == ["overlap"]
    assert items[other]["outdated"] == []
    assert items[stale]["overlapping"] == [other]
    assert items[other]["overlapping"] == [stale]
    assert items[near_a]["nearby_creates"] == [near_b]
    assert items[near_b]["nearby_creates"] == [near_a]
    assert items[far]["nearby_creates"] == [] and items[far]["overlapping"] == []
    assert _ids(_queue(api, outdated="true")) == [stale]
    assert stale not in _ids(_queue(api, outdated="false"))
    assert items[stale]["intent"] == "edit" and items[near_a]["intent"] == "create"


def _revision(archive: Archive, record_id: int) -> int:
    """The record's latest Revision: the Base revision of an edit written now."""

    async def latest(store: PostgresArchiveStore) -> int:
        found = await store.connection.scalar(
            text("SELECT max(id) FROM revision WHERE record_id = :record"), {"record": record_id}
        )
        assert found is not None
        return int(found)

    return archive.read(latest)


def test_the_queue_answers_401_and_403(api: Api, callers: Callers) -> None:
    callers.anonymous()
    assert api.client.get("/api/moderation/queue").status_code == 401

    callers.be("ada")
    response = api.client.get("/api/moderation/queue")

    assert response.status_code == 403
    assert response.json() == {"code": "moderator_only"}
    assert api.client.post("/api/contributions/1/notes", json={"text": "x"}).status_code == 403


# Criterion 33 and 37: identity, notes, and who may read a Submission.


def test_criterion_33_no_response_to_a_non_moderator_holds_a_note_or_a_moderators_identity(
    api: Api, callers: Callers, migrated_database: str
) -> None:
    ada = callers.be("ada")

    async def work(connection: AsyncConnection) -> int:
        return await submitted(connection, ada)

    submission = run(migrated_database, work)
    callers.be("gus", moderator=True)
    noted = api.client.post(
        f"/api/contributions/{submission}/notes", json={"text": "Controllare la liberatoria."}
    )
    assert noted.status_code == 201, noted.text
    version = noted.json()["version"]
    rejected = api.client.post(
        f"/api/contributions/{submission}/decision",
        json={
            "verdict": "reject",
            "version": version,
            "reason": "evidence",
            "text": "Mancano prove.",
        },
    )
    assert rejected.status_code == 200, rejected.text
    seen_by_moderator = api.client.get(f"/api/contributions/{submission}").json()

    callers.be("ada")
    seen_by_submitter = api.client.get(f"/api/contributions/{submission}")

    assert [note["text"] for note in seen_by_moderator["notes"]] == ["Controllare la liberatoria."]
    assert seen_by_moderator["notes"][0]["author"]["display_name"] == "Gus"
    decision = seen_by_moderator["log"][-1]
    assert decision["actor"] == {"role": "moderator", "user": decision["actor"]["user"]}
    assert decision["actor"]["user"]["display_name"] == "Gus"
    body = seen_by_submitter.json()
    assert body["notes"] == []
    assert body["log"][-1]["actor"] == {"role": "moderator", "user": None}
    assert body["log"][-1]["message"] == "Mancano prove."
    text = seen_by_submitter.text
    assert "Controllare la liberatoria" not in text
    assert "Gus" not in text and "gus@" not in text


def test_criterion_33_a_note_is_immutable_and_only_a_moderator_adds_one(
    api: Api, callers: Callers, migrated_database: str
) -> None:
    ada = callers.be("ada")
    submission = run(migrated_database, lambda connection: submitted(connection, ada))

    assert (
        api.client.post(f"/api/contributions/{submission}/notes", json={"text": "x"}).status_code
        == 403
    )

    callers.be("gus", moderator=True)
    first = api.client.post(f"/api/contributions/{submission}/notes", json={"text": "Uno."})
    second = api.client.post(f"/api/contributions/{submission}/notes", json={"text": "Due."})
    blank = api.client.post(f"/api/contributions/{submission}/notes", json={"text": "  "})

    assert [note["text"] for note in second.json()["notes"]] == ["Uno.", "Due."]
    assert first.json()["notes"][0]["at"] == second.json()["notes"][0]["at"]
    assert blank.status_code == 422 and blank.json() == {"code": "moderation.note_required"}
    assert (
        api.client.put(f"/api/contributions/{submission}/notes", json={"text": "x"}).status_code
        == 405
    )
    assert api.client.delete(f"/api/contributions/{submission}/notes").status_code == 405


def test_criterion_37_only_the_submitter_and_moderators_read_a_submission_and_no_email_is_sent(
    api: Api, callers: Callers, migrated_database: str
) -> None:
    ada = callers.be("ada")
    submission = run(migrated_database, lambda connection: submitted(connection, ada))

    callers.be("mallory")
    for path in ("", "/comparison"):
        assert api.client.get(f"/api/contributions/{submission}{path}").status_code == 404
    callers.anonymous()
    assert api.client.get(f"/api/contributions/{submission}").status_code == 401

    callers.be("gus", moderator=True)
    pages = [
        api.client.get(f"/api/contributions/{submission}"),
        api.client.get(f"/api/contributions/{submission}/comparison"),
        api.client.get("/api/moderation/queue"),
    ]

    for page in pages:
        assert page.status_code == 200
        assert "@" not in page.text
        assert "ada@example.org" not in page.text
    detail = pages[0].json()
    assert detail["submitter"] == {"number": ada, "display_name": "Ada"}
    assert pages[2].json()["items"][0]["submitter"] == {"number": ada, "display_name": "Ada"}


# Criterion 43: the decision reasons.


def test_criterion_43_the_reasons_are_the_configured_ones_in_file_order_then_duplicate(
    api: Api, callers: Callers, migrated_database: str
) -> None:
    ada = callers.be("ada")
    submission = run(migrated_database, lambda connection: submitted(connection, ada))
    callers.be("gus", moderator=True)

    reasons = [
        entry["key"]
        for entry in api.client.get("/api/config").json()["vocabularies"]["decision_reasons"]
    ]
    rejected = api.client.post(
        f"/api/contributions/{submission}/decision",
        json={
            "verdict": "request_changes",
            "version": api.client.get(f"/api/contributions/{submission}").json()["version"],
            "reason": "duplicate",
            "text": "Sembra la stessa opera di una scheda esistente.",
        },
    )

    assert reasons[-1] == "duplicate" and reasons.index("duplicate") == len(reasons) - 1
    assert len(reasons) > 1 and len(set(reasons)) == len(reasons)
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "changes_requested"
    assert rejected.json()["log"][-1]["reason"] == "duplicate"


# Criterion 52: the comparisons.


def _compare(api: Api, submission: int) -> dict[str, Any]:
    response = api.client.get(f"/api/contributions/{submission}/comparison")
    assert response.status_code == 200, response.text
    return response.json()


def test_criterion_52_a_moved_location_is_compared_with_the_current_one_in_numbers(
    api: Api, callers: Callers, migrated_database: str, archive: Archive
) -> None:
    callers.be("gus", moderator=True)
    here, neighbour = archive.ids(
        archive.write(
            Create(New("a"), location(geometry=north(0))),
            Create(New("b"), location(geometry=north(40))),
        )
    )
    base = _revision(archive, here)

    async def work(connection: AsyncConnection) -> int:
        ada = await user(connection, "ada")
        return await submitted(
            connection,
            ada,
            snapshot(SetField(here, "geometry", north(30))),
            kind=Kind.LOCATION,
            target_id=here,
            base_revisions=(base,),
        )

    submission = run(migrated_database, work)

    compared = _compare(api, submission)

    (geometry,) = compared["geometries"]
    assert geometry["record_kind"] == "location" and geometry["target_id"] == here
    assert geometry["current"]["type"] == "Point"
    assert geometry["proposed"]["type"] == "Point"
    summary = geometry["summary"]
    assert (summary["vertices_before"], summary["vertices_after"]) == (1, 1)
    assert summary["largest_shift_metres"] == pytest.approx(30, abs=1.5)
    assert summary["shift_direction"] == "N"
    assert summary["area_change_square_metres"] is None
    assert [near["id"] for near in geometry["near_locations"]] == [neighbour]
    assert geometry["near_locations"][0]["distance_metres"] == pytest.approx(10, abs=1.5)
    assert compared["images"] == []
    assert compared["current_revision"] == base
    assert [(each["index"], each["current"]["type"]) for each in compared["operations"]] == [
        (0, "Point")
    ]


def test_criterion_52_an_area_is_compared_by_vertices_surface_and_the_locations_it_takes_in(
    api: Api, callers: Callers, migrated_database: str, archive: Archive
) -> None:
    callers.be("gus", moderator=True)
    area_id, kept, entering = archive.ids(
        archive.write(
            Create(
                New("a"),
                Area(name="Quartiere fittizio", geometry=square(12.480, 41.893, 12.484, 41.897)),
            ),
            Create(New("k"), location(geometry=point(12.482, 41.895))),
            Create(New("e"), location(geometry=point(12.487, 41.895))),
        )
    )
    base = _revision(archive, area_id)

    async def work(connection: AsyncConnection) -> int:
        ada = await user(connection, "ada")
        return await submitted(
            connection,
            ada,
            snapshot(SetField(area_id, "geometry", square(12.480, 41.893, 12.490, 41.897))),
            kind=Kind.AREA,
            target_id=area_id,
            base_revisions=(base,),
        )

    submission = run(migrated_database, work)

    (geometry,) = _compare(api, submission)["geometries"]

    summary = geometry["summary"]
    assert geometry["record_kind"] == "area"
    assert (summary["vertices_before"], summary["vertices_after"]) == (4, 4)
    assert summary["area_change_square_metres"] == pytest.approx(221_000, rel=0.05)
    assert summary["shift_direction"] in {"E", "NE", "SE"}
    assert (geometry["locations_entering"], geometry["locations_leaving"]) == (1, 0)
    assert kept and entering


def test_criterion_52_a_new_location_has_no_current_geometry(
    api: Api, callers: Callers, migrated_database: str
) -> None:
    callers.be("gus", moderator=True)
    submission = run(
        migrated_database,
        lambda connection: _create(connection, _new_artwork_at(north(0))),
    )

    (geometry,) = _compare(api, submission)["geometries"]

    assert geometry["current"] is None
    assert geometry["summary"]["vertices_before"] is None
    assert geometry["summary"]["largest_shift_metres"] is None


async def _create(connection: AsyncConnection, content: Any) -> int:
    return await submitted(connection, await user(connection, "ada"), content)


def test_criterion_52_a_proposed_image_is_set_beside_the_latest_image_of_the_artwork(
    api: Api, callers: Callers, migrated_database: str, archive: Archive
) -> None:
    callers.be("gus", moderator=True)
    older = UncertainDate(Precision.YEAR, Qualifier.EXACT, date(2023, 1, 1))
    newer = UncertainDate(Precision.YEAR, Qualifier.EXACT, date(2025, 1, 1))
    _, artwork_id, _, latest, *_ = archive.ids(
        archive.write(
            Create(New("l"), location()),
            Create(New("w"), artwork(New("l"), title="Gatto")),
            Create(New("old"), image(New("w"), file="originals/vecchia.jpg", observed_date=older)),
            Create(
                New("new"),
                image(
                    New("w"),
                    file="originals/recente.jpg",
                    observed_date=newer,
                    creator_credit="Fotografa fittizia",
                ),
            ),
        )
    )
    base = _revision(archive, artwork_id)

    async def work(connection: AsyncConnection) -> int:
        ada = await user(connection, "ada")
        return await submitted(
            connection,
            ada,
            snapshot(
                Create(New("i"), image(artwork_id, file="originals/nuova.jpg", licence="CC0-1.0"))
            ),
            target_id=artwork_id,
            base_revisions=(base,),
        )

    submission = run(migrated_database, work)

    compared = _compare(api, submission)

    (images,) = compared["images"]
    assert images["proposed"]["file"] == "originals/nuova.jpg"
    assert images["proposed"]["licence"] == "CC0-1.0"
    assert images["proposed"]["item_id"] is None
    assert images["current"]["file"] == "originals/recente.jpg"
    assert images["current"]["item_id"] == latest
    assert images["current"]["creator_credit"] == "Fotografa fittizia"
    assert images["current"]["observed_date"]["first"] == "2025-01-01"
    assert compared["geometries"] == []


def test_criterion_52_the_current_value_of_each_field_and_item_and_the_round_history(
    api: Api, callers: Callers, migrated_database: str, archive: Archive
) -> None:
    callers.be("gus", moderator=True)
    _, artwork_id = archive.ids(
        archive.write(
            Create(New("l"), location()),
            Create(New("w"), artwork(New("l"), title="Gatto", history_events=(event(),))),
        )
    )
    base = _revision(archive, artwork_id)

    async def work(connection: AsyncConnection) -> int:
        ada = await user(connection, "ada")
        first = await submitted(
            connection,
            ada,
            snapshot(SetField(artwork_id, "title", "Gatto sul portone")),
            target_id=artwork_id,
            base_revisions=(base,),
        )
        await service.submit(
            connection,
            first,
            ada,
            snapshot(
                SetField(artwork_id, "title", "Gatto sul portone"),
                SetField(artwork_id, "description", "Un gatto fittizio."),
            ),
            NOW + DAY,
            ARCHIVE_RULES,
        )
        return first

    submission = run(migrated_database, work)

    compared = _compare(api, submission)

    assert [(each["index"], each["current"]) for each in compared["operations"]] == [
        (0, "Gatto"),
        (1, None),
    ]
    assert [each["number"] for each in compared["rounds"]] == [1, 2]
    assert [len(each["snapshot"]["operations"]) for each in compared["rounds"]] == [1, 2]
    assert json.dumps(compared["rounds"][0]["snapshot"]) != json.dumps(
        compared["rounds"][1]["snapshot"]
    )


# Criterion 43 and 44: what the Moderator can decide on, by status and ownership.


def test_the_submission_says_which_decisions_the_moderator_may_take(
    api: Api, callers: Callers, migrated_database: str
) -> None:
    ada = callers.be("ada")
    submission = run(migrated_database, lambda connection: submitted(connection, ada))
    assert api.client.get(f"/api/contributions/{submission}").json()["decisions"] == []

    callers.be("gus", moderator=True)
    seen = api.client.get(f"/api/contributions/{submission}").json()
    assert seen["decisions"] == ["approve", "reject", "request_changes"]

    changes = api.client.post(
        f"/api/contributions/{submission}/decision",
        json={
            "verdict": "request_changes",
            "version": seen["version"],
            "reason": "other",
            "text": "Manca una foto.",
        },
    )
    assert changes.json()["decisions"] == ["reject"]


def test_criterion_44_under_self_approval_false_a_moderator_decides_on_nothing_of_their_own(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, migrated_database: str
) -> None:
    instance_with(tmp_path, monkeypatch, "self_approval = true", "self_approval = false")
    with open_api(migrated_database) as api:
        callers = Callers(api)
        gus = callers.be("gus", moderator=True)
        own = run(migrated_database, lambda connection: submitted(connection, gus))
        ada = callers.be("ada")
        other = run(migrated_database, lambda connection: submitted(connection, ada))
        callers.be("gus")

        mine = api.client.get(f"/api/contributions/{own}").json()
        theirs = api.client.get(f"/api/contributions/{other}").json()
        refused = api.client.post(
            f"/api/contributions/{own}/decision",
            json={"verdict": "approve", "version": mine["version"]},
        )
        noted = api.client.post(f"/api/contributions/{own}/notes", json={"text": "Una nota."})

        assert mine["decisions"] == []
        assert theirs["decisions"] == ["approve", "reject", "request_changes"]
        assert refused.status_code == 403
        assert refused.json() == {"code": "moderation.own_submission"}
        assert noted.status_code == 201
