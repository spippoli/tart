"""Discovery spec, The map (Data): acceptance criterion 69. The Locations response for 10,000
fictional Locations is under 1 MB compressed, answers in under 500 ms, and a repeat with its
ETag returns 304. Every record is the fictional dataset's."""

import gzip
import time
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from auth_fixtures import Api, open_api
from conftest import execute
from test_fictional_dataset import _seed

LOCATIONS = 10_000


@pytest.fixture(scope="module")
def big_archive(
    postgres_server: str, migrated_template: str, tmp_path_factory: pytest.TempPathFactory
) -> str:
    """The URL of a database holding the fictional dataset with 10,000 more Locations."""
    name = f"test_{uuid.uuid4().hex}"
    execute(
        f"postgresql://{postgres_server}/postgres",
        f'CREATE DATABASE "{name}" TEMPLATE "{migrated_template}"',
    )
    url = f"postgresql+asyncpg://{postgres_server}/{name}"
    storage = tmp_path_factory.mktemp("storage")
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("DATABASE_URL", url)
        patch.setenv("STORAGE_PATH", str(storage))
        _seed(url, Path(storage), locations=LOCATIONS)
    return url


@pytest.fixture
def big_api(big_archive: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[Api]:
    monkeypatch.setenv("DATABASE_URL", big_archive)
    with open_api(big_archive) as api:
        yield api


def test_ac69_ten_thousand_locations_are_small_fast_and_cached(big_api: Api) -> None:
    client = big_api.client

    timings = []
    for _ in range(3):
        started = time.perf_counter()
        response = client.get("/api/discovery/locations")
        timings.append(time.perf_counter() - started)

    features = response.json()["features"]
    compressed = len(gzip.compress(response.content))
    print(f"\n{len(features)} Locations, {compressed} bytes gzipped, {timings} seconds")
    assert len(features) >= LOCATIONS
    assert compressed < 1_000_000, f"{compressed} bytes compressed"
    assert min(timings) < 0.5, f"{timings} seconds"
    repeat = client.get(
        "/api/discovery/locations", headers={"If-None-Match": response.headers["ETag"]}
    )
    assert repeat.status_code == 304


def test_ac69_a_search_and_a_page_stay_fast_too(big_api: Api) -> None:
    client = big_api.client

    for params in ({"q": "gatto"}, {"condition": ["destroyed"]}, {"order": "title"}, {}):
        started = time.perf_counter()
        response = client.get("/api/discovery/artworks", params=params)
        elapsed = time.perf_counter() - started
        assert response.status_code == 200
        assert elapsed < 1.0, f"{params}: {elapsed} seconds"
