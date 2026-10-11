"""Discovery spec, Basemap tiles: `tart tiles update` and the startup checks.

go-pmtiles is replaced by a stub `pmtiles` on PATH that copies a fixture extract
(a minimal PMTiles v3 file holding only the metadata) or fails; nothing is
downloaded. The boundary is the tests' fictional rectangle around central Rome.
"""

import gzip
import io
import json
import logging
import math
import shutil
import stat
import sys
import urllib.request
from itertools import pairwise
from pathlib import Path

import pytest
from conftest import VALID_CONFIG
from fastapi.testclient import TestClient

from tart import tiles
from tart.api.app import create_app
from tart.cli import main as run_cli
from tart.map.style import BASEMAP_SCHEMA, BASEMAP_URL, STYLE_FILES

BOUNDARY = (12.40, 41.85, 12.56, 41.95)
"""The valid fixture's boundary: west, south, east, north."""

STUB = f"""#!{sys.executable}
import json, os, shutil, sys
with open(os.environ["FAKE_PMTILES_LOG"], "a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")
if os.environ.get("FAKE_PMTILES_FAIL"):
    open(sys.argv[3], "wb").write(b"half a file")
    sys.exit(1)
shutil.copyfile(os.environ["FAKE_PMTILES_EXTRACT"], sys.argv[3])
"""


def write_pmtiles(path: Path, metadata: dict[str, object]) -> Path:
    """A PMTiles v3 file with no tiles and gzip-compressed JSON metadata."""
    body = gzip.compress(json.dumps(metadata).encode())
    header = bytearray(127)
    header[0:7] = b"PMTiles"
    header[7] = 3
    header[8:16] = (127).to_bytes(8, "little")  # root directory, empty
    header[24:32] = (127).to_bytes(8, "little")  # metadata offset
    header[32:40] = len(body).to_bytes(8, "little")
    header[40:48] = header[56:64] = (127 + len(body)).to_bytes(8, "little")
    header[96] = 1  # clustered
    header[97] = header[98] = 2  # gzip
    header[99] = 1  # mvt
    path.write_bytes(bytes(header) + body)
    return path


def protomaps_extract(path: Path, version: str) -> Path:
    return write_pmtiles(path, {"name": "Protomaps Basemap", "version": version})


def use_local_basemap(directory: Path, schema: int = 4) -> None:
    """Make both styles use the symbolic local basemap and declare `schema`."""
    for file in STYLE_FILES.values():
        path = directory / file
        path.parent.mkdir(parents=True, exist_ok=True)
        style = (
            json.loads(path.read_text(encoding="utf-8"))
            if path.exists()
            else {"version": 8, "sources": {}, "layers": []}
        )
        style.setdefault("metadata", {})[BASEMAP_SCHEMA] = schema
        style["sources"]["protomaps"] = {"type": "vector", "url": BASEMAP_URL}
        path.write_text(json.dumps(style), encoding="utf-8")


def use_external_tiles(directory: Path) -> None:
    for file in STYLE_FILES.values():
        path = directory / file
        path.parent.mkdir(parents=True, exist_ok=True)
        style = (
            json.loads(path.read_text(encoding="utf-8"))
            if path.exists()
            else {"version": 8, "sources": {}, "layers": []}
        )
        style.get("metadata", {}).pop(BASEMAP_SCHEMA, None)
        style["sources"] = {
            "external": {"type": "vector", "url": "pmtiles://https://tiles.example.org/a.pmtiles"}
        }
        path.write_text(json.dumps(style), encoding="utf-8")


@pytest.fixture
def config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "config"
    shutil.copytree(VALID_CONFIG, directory)
    use_local_basemap(directory)
    monkeypatch.setenv("CONFIG_DIR", str(directory))
    return directory


@pytest.fixture
def tiles_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "tiles"
    monkeypatch.setenv("PMTILES_PATH", str(directory))
    return directory


class Stub:
    def __init__(self, directory: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.directory = directory
        self.monkeypatch = monkeypatch
        self.log = directory / "calls.jsonl"
        self.log.touch()
        monkeypatch.setenv("FAKE_PMTILES_LOG", str(self.log))
        self.serves("4.15.2")

    def serves(self, version: str) -> None:
        extract = protomaps_extract(self.directory / f"{version}.pmtiles", version)
        self.monkeypatch.setenv("FAKE_PMTILES_EXTRACT", str(extract))
        self.monkeypatch.delenv("FAKE_PMTILES_FAIL", raising=False)

    def fails(self) -> None:
        self.monkeypatch.setenv("FAKE_PMTILES_FAIL", "1")

    @property
    def calls(self) -> list[list[str]]:
        return [json.loads(line) for line in self.log.read_text().splitlines()]


@pytest.fixture
def pmtiles(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Stub:
    directory = tmp_path / "bin"
    directory.mkdir()
    program = directory / "pmtiles"
    program.write_text(STUB, encoding="utf-8")
    program.chmod(program.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{directory}:{Path(sys.executable).parent}")
    return Stub(directory, monkeypatch)


def update(*arguments: str) -> int:
    return run_cli(["tiles", "update", *arguments])


def manifest(tiles_dir: Path) -> dict[str, str]:
    return json.loads((tiles_dir / tiles.MANIFEST).read_text(encoding="utf-8"))


def extracts(tiles_dir: Path) -> list[str]:
    return sorted(path.name for path in tiles_dir.iterdir() if path.name != tiles.MANIFEST)


def inside(point: tuple[float, float], multipolygon: dict) -> bool:
    """Even-odd ray casting over each outer ring."""
    x, y = point
    for polygon in multipolygon["coordinates"]:
        ring = polygon[0]
        crossings = 0
        for (x1, y1), (x2, y2) in pairwise(ring):
            if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                crossings += 1
        if crossings % 2:
            return True
    return False


def offset(lon: float, lat: float, east_m: float, north_m: float) -> tuple[float, float]:
    return (
        lon + east_m / (111_320 * math.cos(math.radians(lat))),
        lat + north_m / 110_574,
    )


# AC 46: `tart tiles update` extracts the boundary plus 2 km, refuses a schema-major
# mismatch, swaps atomically with a manifest, keeps the previous file, and leaves the
# current file in place on failure.


def test_ac_46_extracts_the_boundary_plus_2_km_and_writes_the_manifest(
    config: Path, tiles_dir: Path, pmtiles: Stub, tmp_path: Path
) -> None:
    assert update("--build", "20261011") == 0

    [call] = pmtiles.calls
    assert call[:2] == ["extract", "https://build.protomaps.com/20261011.pmtiles"]
    assert call[3].startswith("--region=")
    assert manifest(tiles_dir) == {
        "file": "basemap-20261011.pmtiles",
        "build": "20261011",
        "schema_version": "4.15.2",
        "boundary_sha256": tiles.boundary_hash(tiles.boundary_geometry(config)),
    }
    assert extracts(tiles_dir) == ["basemap-20261011.pmtiles"]
    assert tiles.basemap_version(tiles_dir / "basemap-20261011.pmtiles") == "4.15.2"


def test_ac_46_the_region_is_the_boundary_buffered_by_2_km(config: Path) -> None:
    region = tiles.buffered_region(tiles.boundary_geometry(config))
    west, south, east, north = BOUNDARY
    middle_lat = (south + north) / 2

    assert region["type"] == "MultiPolygon"
    covered = [
        (12.48, 41.90),  # inside the boundary
        offset(east, middle_lat, 1900, 0),  # 1.9 km beyond an edge
        offset(west, middle_lat, -1900, 0),
        offset(12.48, north, 0, 1900),
        offset(12.48, south, 0, -1900),
        offset(east, north, 1300, 1300),  # 1.84 km diagonally beyond a corner
    ]
    for point in covered:
        assert inside(point, region), point
    outside = [
        offset(east, middle_lat, 2300, 0),
        offset(12.48, south, 0, -2300),
        offset(east, north, 1500, 1500),  # 2.12 km beyond the corner
    ]
    for point in outside:
        assert not inside(point, region), point


def test_ac_46_keeps_the_previous_file_and_deletes_older_ones(
    config: Path, tiles_dir: Path, pmtiles: Stub
) -> None:
    assert update("--build", "20260401") == 0
    assert update("--build", "20261001") == 0

    assert extracts(tiles_dir) == ["basemap-20260401.pmtiles", "basemap-20261001.pmtiles"]
    assert manifest(tiles_dir)["file"] == "basemap-20261001.pmtiles"

    assert update("--build", "20261011") == 0

    assert extracts(tiles_dir) == ["basemap-20261001.pmtiles", "basemap-20261011.pmtiles"]
    assert manifest(tiles_dir)["file"] == "basemap-20261011.pmtiles"


def test_ac_46_refuses_a_schema_major_mismatch(
    config: Path, tiles_dir: Path, pmtiles: Stub, capsys: pytest.CaptureFixture[str]
) -> None:
    assert update("--build", "20260401") == 0
    before = manifest(tiles_dir)
    pmtiles.serves("5.0.0")

    assert update("--build", "20261011") == 1

    assert "schema 5.0.0" in capsys.readouterr().err
    assert manifest(tiles_dir) == before
    assert extracts(tiles_dir) == ["basemap-20260401.pmtiles"]


def test_ac_46_a_failed_extraction_leaves_the_current_file_in_place(
    config: Path, tiles_dir: Path, pmtiles: Stub
) -> None:
    assert update("--build", "20260401") == 0
    before = manifest(tiles_dir)
    pmtiles.fails()

    assert update("--build", "20261011") == 1

    assert manifest(tiles_dir) == before
    assert extracts(tiles_dir) == ["basemap-20260401.pmtiles"]
    assert tiles.current_extract(tiles_dir) is not None


def test_ac_46_takes_the_latest_build_by_default(
    config: Path, tiles_dir: Path, pmtiles: Stub, monkeypatch: pytest.MonkeyPatch
) -> None:
    builds = [
        {"key": "20261010.pmtiles", "version": "4.15.2"},
        {"key": "20261011.pmtiles", "version": "4.15.2"},
        {"key": "20260930.pmtiles", "version": "4.15.1"},
    ]
    requested: list[str] = []

    def urlopen(request: urllib.request.Request, timeout: float) -> io.BytesIO:
        requested.append(request.full_url)
        return io.BytesIO(json.dumps(builds).encode())

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    assert update() == 0

    assert requested == [tiles.BUILDS_URL]
    assert pmtiles.calls[0][1] == "https://build.protomaps.com/20261011.pmtiles"
    assert manifest(tiles_dir)["build"] == "20261011"


def test_ac_46_source_points_to_a_mirror(config: Path, tiles_dir: Path, pmtiles: Stub) -> None:
    assert update("--build", "20261011", "--source", "https://mirror.example.org/protomaps/") == 0

    assert pmtiles.calls[0][1] == "https://mirror.example.org/protomaps/20261011.pmtiles"


def test_ac_46_source_without_build_is_refused(
    config: Path, tiles_dir: Path, pmtiles: Stub
) -> None:
    assert update("--source", "https://mirror.example.org") == 1
    assert pmtiles.calls == []


def test_ac_46_a_style_without_a_basemap_schema_is_refused(
    config: Path, tiles_dir: Path, pmtiles: Stub, capsys: pytest.CaptureFixture[str]
) -> None:
    use_external_tiles(config)

    assert update("--build", "20261011") == 1

    assert BASEMAP_SCHEMA in capsys.readouterr().err
    assert pmtiles.calls == []


def test_ac_46_an_invalid_build_date_is_refused(config: Path, tiles_dir: Path) -> None:
    with pytest.raises(SystemExit):
        update("--build", "20261340")


# AC 47: startup warns, without stopping, on a missing extract, a changed boundary,
# or a schema mismatch.


def test_ac_47_warns_on_a_missing_extract(config: Path, tiles_dir: Path) -> None:
    [warning] = tiles.startup_warnings(config, tiles_dir)
    assert "missing" in warning


def test_ac_47_warns_when_the_manifest_names_a_deleted_file(
    config: Path, tiles_dir: Path, pmtiles: Stub
) -> None:
    assert update("--build", "20261011") == 0
    (tiles_dir / "basemap-20261011.pmtiles").unlink()

    [warning] = tiles.startup_warnings(config, tiles_dir)
    assert "missing" in warning


def test_ac_47_warns_on_a_changed_boundary(config: Path, tiles_dir: Path, pmtiles: Stub) -> None:
    assert update("--build", "20261011") == 0
    boundary = config / "geography" / "boundary.geojson"
    boundary.write_text(boundary.read_text().replace("12.56", "12.60"), encoding="utf-8")

    [warning] = tiles.startup_warnings(config, tiles_dir)
    assert "boundary changed" in warning


def test_ac_47_a_reformatted_boundary_is_not_a_change(
    config: Path, tiles_dir: Path, pmtiles: Stub
) -> None:
    assert update("--build", "20261011") == 0
    boundary = config / "geography" / "boundary.geojson"
    boundary.write_text(json.dumps(json.loads(boundary.read_text()), indent=4), encoding="utf-8")

    assert tiles.startup_warnings(config, tiles_dir) == []


def test_ac_47_warns_on_a_schema_mismatch(config: Path, tiles_dir: Path, pmtiles: Stub) -> None:
    assert update("--build", "20261011") == 0
    use_local_basemap(config, schema=5)

    [warning] = tiles.startup_warnings(config, tiles_dir)
    assert "schema 4.15.2" in warning


def test_ac_47_no_warning_for_a_current_extract(
    config: Path, tiles_dir: Path, pmtiles: Stub
) -> None:
    assert update("--build", "20261011") == 0

    assert tiles.startup_warnings(config, tiles_dir) == []


def test_ac_47_warns_on_a_missing_extract_named_in_a_tiles_array(
    config: Path, tiles_dir: Path
) -> None:
    for file in STYLE_FILES.values():
        path = config / file
        style = json.loads(path.read_text(encoding="utf-8"))
        style["sources"]["basemap"] = {"type": "vector", "tiles": [BASEMAP_URL]}
        path.write_text(json.dumps(style), encoding="utf-8")

    [warning] = tiles.startup_warnings(config, tiles_dir)
    assert "missing" in warning


def test_ac_47_no_check_applies_to_external_tiles(config: Path, tiles_dir: Path) -> None:
    use_external_tiles(config)

    assert tiles.startup_warnings(config, tiles_dir) == []


def test_ac_47_the_api_starts_and_logs_the_warning(
    database: str, config: Path, tiles_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    run_cli(["migrate"])

    with caplog.at_level(logging.WARNING), TestClient(create_app()) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert any(
        "basemap" in record.getMessage() and "missing" in record.getMessage()
        for record in caplog.records
    )
