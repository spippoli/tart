"""Contribution and moderation spec: the contribution API, drafts, terms, and rate limits
(criteria 10, 11, 42, 56, 57, 58, and 59), through the HTTP API with a controllable clock,
filesystem storage in a temporary directory, and the worker's jobs run directly.

Every User, record, and file is fictional.
"""

import asyncio
import json
import uuid
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx2
import pytest
from archive_fixtures import artwork, image, location
from auth_fixtures import Api, instance_with, open_api
from conftest import ENVIRONMENT
from media_fixtures import jpeg_with_gps

from tart import rate_limits
from tart.archive import Condition, Create, Medium, New
from tart.archive.records import DocumentationItem
from tart.db import create_engine
from tart.media.uploads import process_upload
from tart.media.uploads import sweep as sweep_uploads
from tart.moderation import Content, encode_content
from tart.moderation_persistence import limits, retention
from tart.storage.filesystem import FilesystemStorage

KEY = ENVIRONMENT["SESSION_KEY"].encode()
LOCATION, ARTWORK = New("location"), New("artwork")
DAY = timedelta(days=1)
LABELS = ["adds_documentation", "adds_history_event", "changes_condition"]
"""A new Artwork with an image and its initial Condition."""


@pytest.fixture
def storage_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "storage"
    monkeypatch.setenv("STORAGE_PATH", str(path))
    return path


@pytest.fixture
def api(migrated_database: str, storage_path: Path) -> Iterator[Api]:
    with open_api(migrated_database) as started:
        yield started


def _run(api: Api, work: Callable[[Any], Any]) -> Any:
    async def go() -> Any:
        engine = create_engine(api.dsn.replace("postgresql://", "postgresql+asyncpg://"))
        try:
            return await work(engine)
        finally:
            await engine.dispose()

    return asyncio.run(go())


_SESSIONS: dict[tuple[int, str], httpx2.Cookies] = {}
"""The cookies of each signed-in User, by client: signing in again would meet the per-IP
limit on sign-in codes."""


def _as(api: Api, email: str, *, moderator: bool = False, fresh: bool = False) -> int:
    """Be the User: sign in (registering them) the first time, then reuse the session."""
    key = (id(api.client), email)
    api.client.cookies.clear()
    if key in _SESSIONS and not fresh:
        api.client.cookies.update(_SESSIONS[key])
        number = api.client.get("/api/auth/session").json()["user"]["number"]
    else:
        number = api.sign_in(email)
        _SESSIONS[key] = httpx2.Cookies(api.client.cookies)
    if moderator:
        api.query(
            "INSERT INTO user_role (user_id, role) VALUES ($1, 'moderator') ON CONFLICT DO NOTHING",
            number,
        )
    return number


def _upload(api: Api) -> str:
    response = api.client.post(
        "/api/media", files={"file": ("foto.jpg", jpeg_with_gps(), "image/jpeg")}
    )
    assert response.status_code == 202, response.text
    return response.json()["id"]


def _process(api: Api, storage_path: Path) -> None:
    """Run every deferred processing job, as the worker would."""
    jobs = api.query("SELECT args FROM procrastinate_jobs WHERE task_name = 'process_upload'")
    storage = FilesystemStorage(storage_path)

    async def work(engine: Any) -> None:
        for job in jobs:
            args = json.loads(job["args"])
            await process_upload(
                engine, storage, uuid.UUID(args["upload_id"]), args["cap"], api.clock.now
            )

    _run(api, work)
    api.query("DELETE FROM procrastinate_jobs WHERE task_name = 'process_upload'")


def _objects(storage_path: Path) -> set[str]:
    return {
        str(path.relative_to(storage_path))
        for path in storage_path.rglob("*")
        if path.is_file() and ".partial" not in path.parts
    }


def _retention(api: Api, storage_path: Path, at: datetime) -> None:
    _run(api, lambda engine: retention.sweep(engine, FilesystemStorage(storage_path), at, 90))


def _ids(api: Api) -> list[int]:
    return [row["id"] for row in api.query("SELECT id FROM submission ORDER BY id")]


def _content(*files: str, links: int = 0, target: int | None = None) -> dict[str, Any]:
    """A new Artwork with one image per file, and `links` link Documentation items; or, with
    a `target`, documentation added to that existing Artwork."""
    about: Any = target if target is not None else ARTWORK
    items: list[Create] = [
        Create(New(f"image-{index}"), image(about, file=file)) for index, file in enumerate(files)
    ] + [
        Create(
            New(f"link-{index}"),
            DocumentationItem(
                medium=Medium.LINK,
                observed_date=image(ARTWORK).observed_date,
                artworks=(about,),
                url=f"https://example.org/fictional/{index}",
                language="it",
            ),
        )
        for index in range(links)
    ]
    if target is not None:
        return encode_content(Content(tuple(items)))  # type: ignore[return-value]
    operations = (
        Create(LOCATION, location()),
        Create(ARTWORK, artwork(LOCATION, history_events=())),
        *items,
    )
    return encode_content(Content(operations, Condition.INTACT))  # type: ignore[return-value]


def _start(api: Api, **body: Any):
    return api.client.post("/api/contributions", json={"target_kind": "artwork", **body})


def _draft(api: Api, content: dict[str, Any] | None = None) -> int:
    response = _start(api)
    assert response.status_code == 201, response.text
    submission_id = response.json()["id"]
    if content is not None:
        saved = api.client.put(
            f"/api/contributions/{submission_id}/working-copy", json={"content": content}
        )
        assert saved.status_code == 200, saved.text
    return submission_id


def _submit(api: Api, submission_id: int, **body: Any):
    return api.client.post(f"/api/contributions/{submission_id}/submit", json=body)


def _get(api: Api, submission_id: int) -> dict[str, Any]:
    response = api.client.get(f"/api/contributions/{submission_id}")
    assert response.status_code == 200, response.text
    return response.json()


def _decide(api: Api, submission_id: int, verdict: str, **body: Any):
    version = _get(api, submission_id)["version"]
    return api.client.post(
        f"/api/contributions/{submission_id}/decision",
        json={"verdict": verdict, "version": version, **body},
    )


def _reject(api: Api, submission_id: int, moderator: str = "gus@example.org"):
    submitter = httpx2.Cookies(api.client.cookies)
    _as(api, moderator, moderator=True)
    response = _decide(api, submission_id, "reject", reason="evidence", text="Not enough proof.")
    assert response.status_code == 200, response.text
    api.client.cookies.clear()
    api.client.cookies.update(submitter)


# The lifecycle through the API.


def test_a_submitter_drafts_autosaves_and_submits_and_nobody_else_sees_it(api: Api) -> None:
    _as(api, "ada@example.org")
    file = _upload(api)
    draft = _draft(api, _content(file))

    submitted = _submit(api, draft, accept_terms=True, note="Fotografata ieri.")

    assert submitted.status_code == 200, submitted.text
    body = submitted.json()
    assert (body["status"], body["rounds"], body["intent"]) == ("submitted", 1, "create")
    assert body["labels"] == LABELS
    assert body["last_round"] == _content(file)
    _as(api, "mallory@example.org")
    assert api.client.get(f"/api/contributions/{draft}").status_code == 404
    assert _submit(api, draft, accept_terms=True).status_code == 404
    assert api.client.delete(f"/api/contributions/{draft}").status_code == 404
    assert api.client.get("/api/contributions").json() == {"items": []}


def test_moderators_decide_and_the_submitter_never_learns_who(api: Api) -> None:
    submitter = _as(api, "ada@example.org")
    draft = _draft(api, _content(_upload(api)))
    _submit(api, draft, accept_terms=True)
    moderator = _as(api, "gus@example.org", moderator=True)

    refused = api.client.post(
        f"/api/contributions/{draft}/decision",
        json={"verdict": "reject", "version": 1, "reason": "evidence"},
    )
    rejected = _decide(api, draft, "reject", reason="evidence", text="Prove it.")

    assert refused.status_code == 422
    assert refused.json() == {"code": "moderation.decision_text_required"}
    assert rejected.status_code == 200
    seen_by_moderator = [e["actor"] for e in rejected.json()["log"]]
    assert seen_by_moderator[-1] == {
        "role": "moderator",
        "user": {"number": moderator, "display_name": "Lettrice di prova"},
    }
    _as(api, "ada@example.org")
    log = _get(api, draft)["log"]
    assert [e["actor"] for e in log] == [
        {"role": "submitter", "user": None},
        {"role": "moderator", "user": None},
    ]
    assert "display_name" not in json.dumps(log)
    assert _get(api, draft)["submitter"]["number"] == submitter


def test_a_stranger_who_is_not_a_moderator_cannot_decide_and_gets_a_translatable_code(
    api: Api,
) -> None:
    _as(api, "ada@example.org")
    draft = _draft(api, _content(_upload(api)))
    _submit(api, draft, accept_terms=True)

    response = _decide(api, draft, "approve")

    assert response.status_code == 403
    assert response.json() == {"code": "moderation.forbidden"}


def test_an_invalid_changeset_is_refused_on_submit_and_the_draft_keeps_its_content(
    api: Api,
) -> None:
    _as(api, "ada@example.org")
    content = _content(_upload(api))
    content["initial_condition"] = None
    draft = _draft(api, content)

    response = _submit(api, draft, accept_terms=True)

    assert response.status_code == 422
    assert response.json() == {"code": "moderation.initial_condition_required"}
    again = _get(api, draft)
    assert (again["status"], again["working_copy"]) == ("draft", content)


def test_the_submitter_retracts_and_a_file_of_another_user_cannot_be_attached(api: Api) -> None:
    _as(api, "mallory@example.org")
    stolen = _upload(api)
    _as(api, "ada@example.org")
    draft = _draft(api)

    attach = api.client.put(
        f"/api/contributions/{draft}/working-copy", json={"content": _content(stolen)}
    )
    api.client.put(
        f"/api/contributions/{draft}/working-copy", json={"content": _content(_upload(api))}
    )
    _submit(api, draft, accept_terms=True)
    retracted = api.client.post(f"/api/contributions/{draft}/retract")

    assert attach.status_code == 422
    assert attach.json() == {"code": "moderation.file_not_found"}
    assert retracted.json()["status"] == "retracted"
    assert api.client.post(f"/api/contributions/{draft}/retract").status_code == 409


# Criterion 10.


def test_criterion_10_a_draft_never_edited_is_discarded_after_24_hours(
    api: Api, storage_path: Path
) -> None:
    _as(api, "ada@example.org")
    never_edited = _draft(api)
    edited = _draft(api, _content(_upload(api)))

    _retention(api, storage_path, api.clock.now + DAY - timedelta(minutes=1))
    assert _ids(api) == [never_edited, edited]
    _retention(api, storage_path, api.clock.now + DAY)

    assert _ids(api) == [edited]


def test_criterion_10_a_draft_abandoned_for_the_expiry_is_deleted_with_its_media(
    api: Api, storage_path: Path
) -> None:
    _as(api, "ada@example.org")
    file = _upload(api)
    _process(api, storage_path)
    draft = _draft(api, _content(file))
    saved_at = api.clock.now
    assert _objects(storage_path) != set()

    # The hourly sweep of uploads leaves an attached upload alone.
    _run(
        api,
        lambda engine: sweep_uploads(engine, FilesystemStorage(storage_path), saved_at + DAY * 2),
    )
    _retention(api, storage_path, saved_at + timedelta(days=90) - timedelta(minutes=1))
    assert api.query("SELECT id FROM submission") != []
    assert _objects(storage_path) != set()
    _retention(api, storage_path, saved_at + timedelta(days=90))

    assert api.query("SELECT id FROM submission") == []
    assert api.query("SELECT id FROM upload") == []
    assert _objects(storage_path) == set()
    assert draft


def test_criterion_10_the_media_of_a_draft_are_never_served_publicly(
    api: Api, storage_path: Path
) -> None:
    _as(api, "ada@example.org")
    file = _upload(api)
    _process(api, storage_path)
    _draft(api, _content(file))

    own = api.client.get(f"/api/media/{file}/thumbnail")
    api.client.cookies.clear()
    anonymous = api.client.get(f"/api/media/{file}/thumbnail")
    _as(api, "mallory@example.org")
    stranger = api.client.get(f"/api/media/{file}/thumbnail")
    _as(api, "gus@example.org", moderator=True)
    moderator = api.client.get(f"/api/media/{file}/thumbnail")

    assert [own.status_code, anonymous.status_code, stranger.status_code] == [200, 404, 404]
    assert moderator.status_code == 200


def test_criterion_10_deleting_a_draft_deletes_its_media_and_nothing_else(
    api: Api, storage_path: Path
) -> None:
    _as(api, "ada@example.org")
    file = _upload(api)
    _process(api, storage_path)
    draft = _draft(api, _content(file))

    response = api.client.delete(f"/api/contributions/{draft}")

    assert response.status_code == 204
    assert api.query("SELECT id FROM submission") == []
    assert _objects(storage_path) == set()


# Criteria 11 and 42.


def test_criterion_11_a_user_who_has_not_accepted_the_current_terms_cannot_submit(
    api: Api,
) -> None:
    _as(api, "ada@example.org")
    draft = _draft(api, _content(_upload(api)))

    state = api.client.get("/api/contributions/terms").json()
    refused = _submit(api, draft)

    assert state == {"version": 1, "accepted_version": None, "acceptance_required": True}
    assert refused.status_code == 409
    assert refused.json() == {"code": "moderation.terms_not_accepted"}
    assert _get(api, draft)["status"] == "draft"
    assert api.query("SELECT user_id FROM user_terms_acceptance") == []
    assert _submit(api, draft, accept_terms=True).status_code == 200
    assert [r["version"] for r in api.query("SELECT version FROM user_terms_acceptance")] == [1]


def test_criterion_42_a_new_terms_version_asks_again_and_spares_submitted_work(
    migrated_database: str,
    storage_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with open_api(migrated_database) as first:
        _as(first, "ada@example.org")
        cookies = httpx2.Cookies(first.client.cookies)
        before = _draft(first, _content(_upload(first)))
        _submit(first, before, accept_terms=True)
        state = first.client.get("/api/contributions/terms").json()
        second_draft = _draft(first, _content(_upload(first)))
        assert _submit(first, second_draft).status_code == 200
    assert state == {"version": 1, "accepted_version": 1, "acceptance_required": False}

    instance_with(tmp_path, monkeypatch, "[terms]\nversion = 1", "[terms]\nversion = 2")
    with open_api(migrated_database) as restarted:
        restarted.client.cookies.update(cookies)
        state = restarted.client.get("/api/contributions/terms").json()
        draft = _draft(restarted, _content(_upload(restarted)))
        refused = _submit(restarted, draft)
        accepted = _submit(restarted, draft, accept_terms=True)

        assert state == {"version": 2, "accepted_version": 1, "acceptance_required": True}
        assert refused.json() == {"code": "moderation.terms_not_accepted"}
        assert accepted.status_code == 200
        assert _get(restarted, before)["status"] == "submitted"
        assert _get(restarted, second_draft)["status"] == "submitted"
        assert restarted.client.get("/api/contributions/terms").json()["accepted_version"] == 2


# Criterion 56.


def test_criterion_56_media_go_after_30_days_and_only_a_stub_remains_after_12_months(
    api: Api, storage_path: Path
) -> None:
    _as(api, "ada@example.org")
    file = _upload(api)
    _process(api, storage_path)
    draft = _draft(api, _content(file))
    _submit(api, draft, accept_terms=True, note="Una nota.")
    _reject(api, draft)
    rejected_at = api.clock.now
    assert _objects(storage_path) != set()

    _retention(api, storage_path, rejected_at + timedelta(days=30) - timedelta(minutes=1))
    assert _objects(storage_path) != set()
    _retention(api, storage_path, rejected_at + timedelta(days=30))

    assert _objects(storage_path) == set()
    assert api.client.get(f"/api/media/{file}").json()["status"] == "deleted"
    assert api.client.get(f"/api/media/{file}/thumbnail").status_code == 404
    kept = _get(api, draft)
    assert kept["last_round"] == _content(file)
    assert kept["stub"] is False

    _retention(api, storage_path, rejected_at + timedelta(days=365))

    rows = api.query("SELECT reduced_at, stub, working_copy FROM submission")
    assert len(rows) == 1 and rows[0]["reduced_at"] is not None
    assert json.loads(rows[0]["stub"]) == {"labels": LABELS}
    assert [dict(row) for row in api.query("SELECT number, snapshot FROM submission_round")] == [
        {"number": 1, "snapshot": None}
    ]
    api.clock.now = rejected_at + timedelta(days=366)
    _as(api, "ada@example.org", fresh=True)
    stub = _get(api, draft)
    assert (stub["stub"], stub["last_round"], stub["rounds"]) == (True, None, 1)
    assert stub["labels"] == LABELS
    assert [e["event"] for e in stub["log"]] == ["submitted", "rejected"]
    assert stub["log"][1]["reason"] == "evidence"


# Criterion 57.


def test_criterion_57_start_again_copies_the_last_round_and_links_both_submissions(
    api: Api, storage_path: Path
) -> None:
    _as(api, "ada@example.org")
    file = _upload(api)
    _process(api, storage_path)
    original = _draft(api, _content(file))
    _submit(api, original, accept_terms=True)
    assert api.client.post(f"/api/contributions/{original}/start-again").status_code == 409
    _reject(api, original)

    response = api.client.post(f"/api/contributions/{original}/start-again")

    assert response.status_code == 201, response.text
    retry = response.json()
    assert (retry["status"], retry["retry_of"]) == ("draft", original)
    copied = retry["working_copy"]["operations"][-1]["record"]["file"]
    assert copied != file
    assert retry["working_copy"] == _content(copied)
    assert {f"permanent/media/{copied}/original", f"permanent/media/{file}/original"} <= _objects(
        storage_path
    )
    assert [(e["event"], e["related_submission"]) for e in retry["log"]] == [("retry_of", original)]
    kept = _get(api, original)
    assert [(e["event"], e["related_submission"]) for e in kept["log"][-1:]] == [
        ("retried_in", retry["id"])
    ]
    assert kept["status"] == "rejected"
    # The copy is the retry's own: it survives the deletion of the original's media.
    api.client.put(
        f"/api/contributions/{retry['id']}/working-copy", json={"content": retry["working_copy"]}
    )
    _retention(api, storage_path, api.clock.now + timedelta(days=31))
    assert f"permanent/media/{copied}/original" in _objects(storage_path)
    assert f"permanent/media/{file}/original" not in _objects(storage_path)
    # A retry is an ordinary Submission.
    api.clock.now += timedelta(days=31)
    _as(api, "ada@example.org", fresh=True)
    assert api.client.get(f"/api/contributions/{retry['id']}").status_code == 200


def test_criterion_57_start_again_is_for_the_submitter_of_a_rejected_or_retracted_one(
    api: Api,
) -> None:
    _as(api, "ada@example.org")
    draft = _draft(api, _content(_upload(api)))
    _submit(api, draft, accept_terms=True)
    retracted = api.client.post(f"/api/contributions/{draft}/retract")
    _as(api, "gus@example.org", moderator=True)
    by_moderator = api.client.post(f"/api/contributions/{draft}/start-again")
    _as(api, "ada@example.org")

    again = api.client.post(f"/api/contributions/{draft}/start-again")

    assert retracted.json()["status"] == "retracted"
    assert (by_moderator.status_code, by_moderator.json()) == (
        403,
        {"code": "moderation.not_submitter"},
    )
    assert again.status_code == 201


def _approved_artwork(api: Api) -> int:
    """An approved Artwork, made by a first Submitter and approved by a Moderator."""
    _as(api, "prima@example.org")
    first = _draft(api, _content(_upload(api)))
    _submit(api, first, accept_terms=True)
    _as(api, "gus@example.org", moderator=True)
    assert _decide(api, first, "approve").status_code == 200
    (row,) = api.query("SELECT id FROM record WHERE kind = 'artwork'")
    return row["id"]


def test_criterion_57_a_conversion_retracts_the_original_only_when_it_is_submitted(
    api: Api, storage_path: Path
) -> None:
    target = _approved_artwork(api)
    _as(api, "ada@example.org")
    file = _upload(api)
    _process(api, storage_path)
    original = _draft(api, _content(file))
    _submit(api, original, accept_terms=True)
    _as(api, "gus@example.org", moderator=True)
    assert (
        _decide(api, original, "request_changes", reason="evidence", text="Doppione.").status_code
        == 200
    )
    _as(api, "ada@example.org")

    conversion = api.client.post(
        f"/api/contributions/{original}/convert", json={"target_id": target}
    )

    assert conversion.status_code == 201, conversion.text
    draft = conversion.json()
    assert (draft["target_kind"], draft["intent"], draft["target_id"]) == (
        "artwork",
        "edit",
        target,
    )
    assert draft["converts"] == original
    assert draft["working_copy"] == _content(
        draft["working_copy"]["operations"][0]["record"]["file"], target=target
    )
    # Deleting the conversion draft leaves the original as it was.
    before = _get(api, original)
    assert api.client.delete(f"/api/contributions/{draft['id']}").status_code == 204
    assert _get(api, original) == before
    assert before["status"] == "changes_requested"

    draft = api.client.post(
        f"/api/contributions/{original}/convert", json={"target_id": target}
    ).json()
    submitted = _submit(api, draft["id"], accept_terms=True)

    assert submitted.status_code == 200, submitted.text
    closed = _get(api, original)
    assert closed["status"] == "retracted"
    assert [
        (e["event"], e["actor"]["role"], e["related_submission"]) for e in closed["log"][-1:]
    ] == [("converted_into", "system", draft["id"])]
    assert _get(api, draft["id"])["log"][0] == {
        **_get(api, draft["id"])["log"][0],
        "event": "conversion_of",
        "related_submission": original,
    }


# Criterion 58.


def _prefill(api: Api, user: int, limit: rate_limits.Limit, times: int, cost: int = 1) -> None:
    async def work(engine: Any) -> None:
        for _ in range(times):
            async with engine.begin() as connection:
                assert (
                    await rate_limits.hit(
                        connection, [(limit, str(user), cost)], api.clock.now, KEY
                    )
                    is None
                )

    _run(api, work)


def test_criterion_58_the_twenty_first_submission_in_24_hours_answers_429_and_keeps_the_draft(
    api: Api,
) -> None:
    user = _as(api, "ada@example.org")
    content = _content(_upload(api))
    first = _draft(api, content)
    _submit(api, first, accept_terms=True)
    _prefill(api, user, limits.SUBMISSIONS, 18)
    api.clock.advance(hours=1)
    last_allowed = _draft(api, content)
    assert _submit(api, last_allowed).status_code == 200
    draft = _draft(api, content)

    refused = _submit(api, draft)

    assert refused.status_code == 429
    assert refused.json() == {
        "code": "moderation.submissions_limited",
        "retry_after": 23 * 3600,
    }
    assert refused.headers["Retry-After"] == str(23 * 3600)
    kept = _get(api, draft)
    assert (kept["status"], kept["working_copy"]) == ("draft", content)
    api.clock.advance(hours=23)
    _as(api, "ada@example.org")
    assert _submit(api, draft).status_code == 200


def test_criterion_58_a_revision_of_a_submitted_submission_is_not_counted(api: Api) -> None:
    user = _as(api, "ada@example.org")
    content = _content(_upload(api))
    first = _draft(api, content)
    _submit(api, first, accept_terms=True)
    _prefill(api, user, limits.SUBMISSIONS, 19)

    revised = _submit(api, first, content=content, note="Rivista.")

    assert revised.status_code == 200
    assert (revised.json()["status"], revised.json()["rounds"]) == ("submitted", 2)
    assert _submit(api, _draft(api, content)).status_code == 429


def test_criterion_58_the_twenty_first_open_draft_answers_429_with_the_time_to_wait(
    api: Api,
) -> None:
    _as(api, "ada@example.org")
    for _ in range(20):
        _start(api)
    api.clock.advance(hours=2)

    refused = _start(api)

    assert refused.status_code == 429
    assert refused.json() == {"code": "moderation.drafts_limited", "retry_after": 22 * 3600}
    assert len(api.client.get("/api/contributions").json()["items"]) == 20
    _as(api, "gus@example.org", moderator=True)
    assert all(_start(api).status_code == 201 for _ in range(21))


def test_criterion_58_the_hundred_and_first_upload_in_24_hours_answers_429(api: Api) -> None:
    user = _as(api, "ada@example.org")
    _prefill(api, user, limits.UPLOAD_FILES, 100)
    api.clock.advance(hours=3)
    data = ("foto.jpg", jpeg_with_gps(), "image/jpeg")

    refused = api.client.post("/api/media", files={"file": data})

    assert refused.status_code == 429
    assert refused.json() == {"code": "moderation.uploads_limited", "retry_after": 21 * 3600}
    assert api.query("SELECT id FROM upload") == []
    _as(api, "gus@example.org", moderator=True)
    assert api.client.post("/api/media", files={"file": data}).status_code == 202


def test_criterion_58_an_upload_past_1_gb_in_24_hours_answers_429(api: Api) -> None:
    user = _as(api, "ada@example.org")
    data = jpeg_with_gps()
    _prefill(api, user, limits.UPLOAD_BYTES, 1, cost=limits.UPLOAD_BYTES.count - len(data) + 1)

    refused = api.client.post("/api/media", files={"file": ("foto.jpg", data, "image/jpeg")})

    assert refused.status_code == 429
    assert refused.json()["code"] == "moderation.uploads_limited"


def test_criterion_58_rejected_files_count_against_the_upload_limits(api: Api) -> None:
    user = _as(api, "ada@example.org")
    not_an_image = ("nota.jpg", b"not an image", "image/jpeg")
    _prefill(api, user, limits.UPLOAD_FILES, 99)

    accepted = api.client.post("/api/media", files={"file": not_an_image})
    refused = api.client.post("/api/media", files={"file": not_an_image})

    assert (accepted.status_code, refused.status_code) == (202, 429)


# Criterion 59.


def test_criterion_59_a_twenty_first_uploaded_item_is_refused_but_links_can_still_be_added(
    api: Api,
) -> None:
    _as(api, "ada@example.org")
    file = _upload(api)
    draft = _draft(api)
    path = f"/api/contributions/{draft}/working-copy"

    twenty = api.client.put(path, json={"content": _content(*[file] * 20)})
    twenty_one = api.client.put(path, json={"content": _content(*[file] * 21)})
    with_links = api.client.put(path, json={"content": _content(*[file] * 20, links=3)})

    assert twenty.status_code == 200
    assert twenty_one.status_code == 422
    assert twenty_one.json() == {"code": "moderation.too_many_files"}
    assert with_links.status_code == 200
    assert _get(api, draft)["working_copy"] == _content(*[file] * 20, links=3)
    refused_submit = _submit(api, draft, content=_content(*[file] * 21), accept_terms=True)
    assert refused_submit.json() == {"code": "moderation.too_many_files"}
