"""The archive responses the frontend's end-to-end tests serve from their stand-in API.

They are the real API's answers over the fictional dataset (`tart.fictional`), so the
record pages are tested against what the API sends. This test fails when they drift;

    TART_WRITE_FIXTURES=1 uv run pytest tests/archive/test_archive_e2e_fixtures.py

writes them again. Upload ids, random at each seed, are replaced by fixed ones.

Besides the public views, `moderator/` holds what a Moderator gets for a withdrawn
Artwork (the complete record) and for an Artwork with a redacted description, and
`redacted/` what the public gets for the latter.
"""

import json
import os
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from auth_fixtures import Api, open_api
from test_archive_api import WITHDRAWN_AT, _as_moderator, _redact, _withdraw
from test_fictional_dataset import _seed

from tart.api.archive import SEGMENTS
from tart.archive import Kind
from tart.fictional import Seeded

FIXTURES = Path(__file__).parents[3] / "frontend" / "e2e" / "fixtures" / "archive"
UPLOAD = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
INDEXED = (Kind.ARTIST, Kind.SITE, Kind.AREA, Kind.SERIES)


@pytest.fixture
def api(migrated_database: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Api]:
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path))
    seeded = _seed(migrated_database, tmp_path)
    with open_api(migrated_database) as started:
        started.seeded = seeded  # type: ignore[attr-defined]
        yield started


def _fixed_uploads(text: str) -> str:
    uploads: dict[str, str] = {}
    return UPLOAD.sub(
        lambda found: uploads.setdefault(
            found.group(), f"00000000-0000-4000-8000-{len(uploads) + 1:012d}"
        ),
        text,
    )


def _responses(api: Api, seeded: Seeded) -> dict[str, str]:
    files: dict[str, str] = {}

    def get(name: str, path: str) -> None:
        response = api.client.get(f"/api/archive/{path}")
        assert response.status_code == 200, (path, response.text)
        files[name] = json.dumps(response.json(), ensure_ascii=False, indent=1) + "\n"

    for record_id in sorted(seeded.ids.values()):
        [kind] = api.query("SELECT kind FROM record WHERE id = $1", record_id)
        segment = SEGMENTS[Kind(kind["kind"])]
        get(f"{segment}/{record_id}.json", f"{segment}/{record_id}")
        get(f"{segment}/{record_id}.revisions.json", f"{segment}/{record_id}/revisions")
    for kind in INDEXED:
        get(f"{SEGMENTS[kind]}/index.json", SEGMENTS[kind])

    redacted = seeded.ids["onda"]
    _redact(api, redacted, "description")
    get(f"redacted/artworks/{redacted}.json", f"artworks/{redacted}")
    get(f"redacted/artworks/{redacted}.revisions.json", f"artworks/{redacted}/revisions")
    _withdraw(api, seeded.complete_artwork)
    _as_moderator(api)
    for record_id in (seeded.complete_artwork, redacted):
        get(f"moderator/artworks/{record_id}.json", f"artworks/{record_id}")
    files["ids.json"] = json.dumps(seeded.ids, indent=1, sort_keys=True) + "\n"
    return {name: _fixed_uploads(text) for name, text in files.items()}


def test_the_e2e_fixtures_are_the_apis_answers(api: Api) -> None:
    files = _responses(api, api.seeded)  # type: ignore[attr-defined]
    assert WITHDRAWN_AT  # the Moderator fixtures carry this date

    if os.environ.get("TART_WRITE_FIXTURES"):
        for name, text in files.items():
            (FIXTURES / name).parent.mkdir(parents=True, exist_ok=True)
            (FIXTURES / name).write_text(text, encoding="utf-8")
    stale = sorted(
        name
        for name in files
        if not (FIXTURES / name).exists()
        or (FIXTURES / name).read_text(encoding="utf-8") != files[name]
    )
    assert not stale, f"run with TART_WRITE_FIXTURES=1 to update: {stale}"
