"""Foundations spec, 3. Storage and media pipeline: the upload path, serving, caching, and
the cleanup of abandoned uploads (criteria 22, 25, 26, 28, and 51, the app's side).

Through the HTTP API with a controllable clock, filesystem storage in a temporary
directory, and the processing job run from the queue the API deferred to.
"""

import asyncio
import json
import uuid
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from auth_fixtures import Api, instance_with, open_api
from media_fixtures import encode, jpeg_with_gps, picture

from tart.db import create_engine
from tart.media import Rendition
from tart.media.uploads import process_upload, sweep
from tart.storage.filesystem import FilesystemStorage

MIB = 1024 * 1024


@pytest.fixture
def storage_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "storage"
    monkeypatch.setenv("STORAGE_PATH", str(path))
    return path


@pytest.fixture
def api(migrated_database: str, storage_path: Path) -> Iterator[Api]:
    with open_api(migrated_database) as started:
        yield started


def _objects(storage_path: Path) -> set[str]:
    return {
        str(path.relative_to(storage_path))
        for path in storage_path.rglob("*")
        if path.is_file() and ".partial" not in path.parts
    }


def _upload(api: Api, data: bytes, name: str = "foto.jpg", content_type: str = "image/jpeg"):
    return api.client.post("/api/media", files={"file": (name, data, content_type)})


def _run(api: Api, coroutine_factory) -> None:
    async def run() -> None:
        engine = create_engine(api.dsn.replace("postgresql://", "postgresql+asyncpg://"))
        try:
            await coroutine_factory(engine)
        finally:
            await engine.dispose()

    asyncio.run(run())


def _process(api: Api, storage_path: Path) -> None:
    """Run every deferred processing job, as the worker would."""
    jobs = api.query("SELECT args FROM procrastinate_jobs WHERE task_name = 'process_upload'")
    storage = FilesystemStorage(storage_path)

    async def work(engine) -> None:
        for job in jobs:
            args = json.loads(job["args"])
            await process_upload(
                engine, storage, uuid.UUID(args["upload_id"]), args["cap"], api.clock.now
            )

    _run(api, work)
    api.query("DELETE FROM procrastinate_jobs WHERE task_name = 'process_upload'")


def _sweep(api: Api, storage_path: Path, at: datetime) -> None:
    _run(api, lambda engine: sweep(engine, FilesystemStorage(storage_path), at))


def _approve(api: Api, upload_id: str) -> None:
    """Make the upload the file of an approved Documentation item."""
    (record,) = api.query("INSERT INTO record (kind) VALUES ('documentation_item') RETURNING id")
    api.query(
        "INSERT INTO documentation_item (id, medium, observed_date, file) "
        "VALUES ($1, 'image', '{}', $2)",
        record["id"],
        upload_id,
    )


def _sign_in_as(api: Api, email: str, *, moderator: bool = False) -> int:
    api.client.cookies.clear()
    number = api.sign_in(email)
    if moderator:
        api.query("INSERT INTO user_role (user_id, role) VALUES ($1, 'moderator')", number)
    return number


def test_uploading_needs_a_session(api: Api, storage_path: Path) -> None:
    response = _upload(api, jpeg_with_gps())

    assert response.status_code == 401
    assert response.json() == {"code": "sign_in_required"}
    assert _objects(storage_path) == set()


def test_an_upload_is_quarantined_then_processed_into_its_renditions(
    api: Api, storage_path: Path
) -> None:
    _sign_in_as(api, "fotografa@example.org")

    response = _upload(api, jpeg_with_gps(4000, 3000))

    assert response.status_code == 202
    upload_id = response.json()["id"]
    assert response.json()["status"] == "processing"
    assert _objects(storage_path) == {f"quarantine/uploads/{upload_id}"}

    _process(api, storage_path)

    state = api.client.get(f"/api/media/{upload_id}").json()
    assert state["status"] == "ready"
    assert state["format"] == "jpeg"
    assert state["renditions"] == {
        "thumbnail": {"width": 480, "height": 360},
        "view": {"width": 1280, "height": 960},
        "large": {"width": 2048, "height": 1536},
    }
    assert _objects(storage_path) == {
        f"permanent/media/{upload_id}/{name}" for name in ("original", *Rendition)
    }


def test_criterion_22_a_file_over_the_limit_is_refused_and_nothing_is_stored(
    api: Api, storage_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    instance_with(tmp_path, monkeypatch, "max_upload_mb = 25", "max_upload_mb = 1")
    with open_api(api.dsn.replace("postgresql://", "postgresql+asyncpg://")) as small:
        _sign_in_as(small, "fotografa@example.org")

        over = _upload(small, b"\xff\xd8\xff" + bytes(MIB - 2))
        exact = _upload(small, b"\xff\xd8\xff" + bytes(MIB - 3))

        assert over.status_code == 413
        assert over.json() == {"code": "file_too_large"}
        assert exact.status_code == 202
        (row,) = small.query("SELECT id, size FROM upload")
        assert (str(row["id"]), row["size"]) == (exact.json()["id"], MIB)
    assert _objects(storage_path) == {f"quarantine/uploads/{exact.json()['id']}"}


def test_criterion_51_a_declared_length_past_the_limit_and_its_margin_is_refused_unread(
    api: Api, storage_path: Path
) -> None:
    _sign_in_as(api, "fotografa@example.org")

    response = api.client.post(
        "/api/media",
        content=b"",
        headers={
            "Content-Type": "multipart/form-data; boundary=x",
            "Content-Length": str(26 * MIB + 1),
        },
    )

    assert response.status_code == 413
    assert response.json() == {"code": "file_too_large"}
    assert api.query("SELECT id FROM upload") == []


def test_criterion_51_a_request_with_two_files_is_refused(api: Api, storage_path: Path) -> None:
    _sign_in_as(api, "fotografa@example.org")
    data = jpeg_with_gps()

    response = api.client.post(
        "/api/media",
        files=[
            ("file", ("uno.jpg", data, "image/jpeg")),
            ("file", ("due.jpg", data, "image/jpeg")),
        ],
    )

    assert response.status_code == 400
    assert response.json() == {"code": "one_file_per_request"}
    assert api.query("SELECT id FROM upload") == []
    assert _objects(storage_path) == set()


def test_a_request_without_a_file_is_refused(api: Api, storage_path: Path) -> None:
    _sign_in_as(api, "fotografa@example.org")

    form = api.client.post("/api/media", data={"note": "nessun file"})
    raw = api.client.post("/api/media", content=b"not multipart")

    for response in (form, raw):
        assert response.status_code == 400
        assert response.json() == {"code": "file_missing"}
    assert _objects(storage_path) == set()


def test_criterion_23_the_declared_name_and_type_are_ignored(api: Api, storage_path: Path) -> None:
    _sign_in_as(api, "fotografa@example.org")
    png = _upload(api, encode(picture(64, 64), "PNG"), "foto.jpg", "image/jpeg")
    text = _upload(api, b"Una nota, non una foto.", "foto.jpg", "image/jpeg")

    _process(api, storage_path)

    assert api.client.get(f"/api/media/{png.json()['id']}").json()["format"] == "png"
    assert api.client.get(f"/api/media/{text.json()['id']}").json() == {
        "id": text.json()["id"],
        "status": "rejected",
        "error": "file_type_unsupported",
        "format": None,
        "renditions": None,
        "suggestions": None,
    }


def test_criterion_28_a_rejected_file_is_deleted_at_once(api: Api, storage_path: Path) -> None:
    _sign_in_as(api, "fotografa@example.org")
    response = _upload(api, encode(picture(50, 50), "GIF"), "animazione.gif", "image/gif")

    _process(api, storage_path)

    state = api.client.get(f"/api/media/{response.json()['id']}").json()
    assert (state["status"], state["error"]) == ("rejected", "file_type_unsupported")
    assert _objects(storage_path) == set()


def test_criterion_26_suggestions_reach_only_the_uploader_and_no_location_is_stored(
    api: Api, storage_path: Path
) -> None:
    _sign_in_as(api, "fotografa@example.org")
    upload_id = _upload(api, jpeg_with_gps()).json()["id"]
    _process(api, storage_path)

    own = api.client.get(f"/api/media/{upload_id}").json()
    _sign_in_as(api, "moderatrice@example.org", moderator=True)
    moderator = api.client.get(f"/api/media/{upload_id}").json()

    assert own["suggestions"] == {"observed_date": "2025-05-03", "point": [12.4823, 41.8955]}
    assert moderator["status"] == "ready"
    assert moderator["suggestions"] is None
    assert api.query("SELECT count(*) AS n FROM location")[0]["n"] == 0


def test_the_state_of_an_upload_is_hidden_from_others(api: Api, storage_path: Path) -> None:
    _sign_in_as(api, "fotografa@example.org")
    upload_id = _upload(api, jpeg_with_gps()).json()["id"]

    _sign_in_as(api, "altra@example.org")
    other = api.client.get(f"/api/media/{upload_id}")
    api.client.cookies.clear()
    anonymous = api.client.get(f"/api/media/{upload_id}")
    unknown = api.client.get(f"/api/media/{uuid.uuid4()}")

    for response in (other, anonymous, unknown):
        assert response.status_code == 404
        assert response.json() == {"code": "upload_not_found"}


def test_criterion_28_pending_media_reach_only_their_submitter_and_moderators(
    api: Api, storage_path: Path
) -> None:
    _sign_in_as(api, "fotografa@example.org")
    upload_id = _upload(api, jpeg_with_gps()).json()["id"]
    _process(api, storage_path)
    url = f"/api/media/{upload_id}/view"

    own = api.client.get(url)
    _sign_in_as(api, "altra@example.org")
    other = api.client.get(url)
    _sign_in_as(api, "moderatrice@example.org", moderator=True)
    moderator = api.client.get(url)
    api.client.cookies.clear()
    anonymous = api.client.get(url)

    for response in (own, moderator):
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/webp"
        assert response.headers["cache-control"] == "private, no-store"
        assert response.content[8:12] == b"WEBP"
    for response in (other, anonymous):
        assert response.status_code == 404


def test_criterion_28_public_renditions_are_cached_for_an_hour(
    api: Api, storage_path: Path
) -> None:
    _sign_in_as(api, "fotografa@example.org")
    upload_id = _upload(api, jpeg_with_gps()).json()["id"]
    _process(api, storage_path)
    _approve(api, upload_id)
    api.client.cookies.clear()

    response = api.client.get(f"/api/media/{upload_id}/thumbnail")
    again = api.client.get(
        f"/api/media/{upload_id}/thumbnail", headers={"If-None-Match": response.headers["etag"]}
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=3600"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert again.status_code == 304
    assert again.headers["cache-control"] == "public, max-age=3600"


def test_criterion_25_the_original_is_never_served(api: Api, storage_path: Path) -> None:
    _sign_in_as(api, "fotografa@example.org", moderator=True)
    upload_id = _upload(api, jpeg_with_gps()).json()["id"]
    _process(api, storage_path)
    _approve(api, upload_id)

    for path in ("original", "../original", "original.jpg"):
        assert api.client.get(f"/api/media/{upload_id}/{path}").status_code in (404, 422)


def test_criterion_28_an_upload_never_attached_is_deleted_within_25_hours(
    api: Api, storage_path: Path
) -> None:
    _sign_in_as(api, "fotografa@example.org")
    abandoned = _upload(api, jpeg_with_gps()).json()["id"]
    attached = _upload(api, jpeg_with_gps()).json()["id"]
    _process(api, storage_path)
    _approve(api, attached)
    uploaded_at = api.clock.now

    _sweep(api, storage_path, uploaded_at + timedelta(hours=23, minutes=59))
    assert {str(row["id"]) for row in api.query("SELECT id FROM upload")} == {abandoned, attached}

    # The hourly sweep after the 24th hour, at the latest 25 hours after upload.
    _sweep(api, storage_path, uploaded_at + timedelta(hours=25))
    assert {str(row["id"]) for row in api.query("SELECT id FROM upload")} == {attached}
    assert not any(abandoned in name for name in _objects(storage_path))
    assert f"permanent/media/{attached}/original" in _objects(storage_path)
    # The suggestions of what stays go at the same age.
    (row,) = api.query("SELECT suggestions FROM upload")
    assert row["suggestions"] is None
