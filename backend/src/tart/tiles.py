"""The basemap tile pipeline (Discovery spec, Basemap tiles).

    update(config_directory, tiles_directory, build=None, source=None) -> Manifest
    current_extract(tiles_directory) -> Manifest | None
    startup_warnings(config_directory, tiles_directory) -> list[str]

`update` extracts the Instance boundary plus 2 km from a Protomaps daily build with
the bundled go-pmtiles program (`pmtiles`), refuses an extract whose schema major
differs from the one the map styles declare, and swaps it in: versioned files
`basemap-YYYYMMDD.pmtiles` in the tiles directory plus `manifest.json`, written
atomically. The previous file stays for open pages; older ones are deleted. A
failure leaves the current file and the manifest untouched.
"""

import gzip
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

from tart.config import load_instance
from tart.config.instance import BOUNDARY

BUFFER_METRES = 2000
"""The extract covers the boundary buffered by this distance (platform constant)."""

DEFAULT_SOURCE = "https://build.protomaps.com"
"""Where the Protomaps daily builds live, as `<source>/YYYYMMDD.pmtiles`."""
BUILDS_URL = "https://build-metadata.protomaps.dev/builds.json"
"""The list of Protomaps daily builds, read to find the latest one."""

SYMBOLIC_URL = "pmtiles:///tiles/basemap.pmtiles"
"""How a style refers to the local basemap (ADR 0009)."""
SCHEMA_KEY = "tart:basemap-schema"
STYLES = ("map/style.light.json", "map/style.dark.json")

MANIFEST = "manifest.json"
PMTILES_PROGRAM = "pmtiles"

_BUILD = re.compile(r"^\d{8}$")
_EXTRACT = re.compile(r"^basemap-\d{8}\.pmtiles$")
_PARTIAL_SUFFIX = ".partial"

# Metres per degree, for the local projection of the buffer; the error over an
# Instance's extent is far below a tile.
_METRES_PER_DEGREE_LAT = 110_574.0
_METRES_PER_DEGREE_LON_AT_EQUATOR = 111_320.0
_CIRCLE_SEGMENTS = 16


class TilesError(Exception):
    """Why `tart tiles update` refused or failed; the current extract is untouched."""


@dataclass(frozen=True)
class Manifest:
    file: str
    """The current extract's name in the tiles directory, `basemap-YYYYMMDD.pmtiles`."""
    build: str
    """The Protomaps build date, `YYYYMMDD`."""
    schema_version: str
    """The Protomaps basemap version in the extract's metadata, such as `4.15.2`."""
    boundary_sha256: str
    """The hash of the boundary the extract was cut from (`boundary_hash`)."""

    @property
    def schema_major(self) -> int | None:
        return _major(self.schema_version)


def is_build(value: str) -> bool:
    """Whether `value` is a build date, `YYYYMMDD`."""
    if not _BUILD.match(value):
        return False
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError:
        return False
    return True


def _major(version: str) -> int | None:
    head = version.split(".", 1)[0]
    return int(head) if head.isdigit() else None


# The boundary and the extract area


def boundary_geometry(config_directory: Path) -> dict[str, Any]:
    """The boundary's Polygon or MultiPolygon; the loader has already validated the file."""
    geojson = json.loads((config_directory / BOUNDARY).read_text(encoding="utf-8"))
    if geojson.get("type") == "FeatureCollection":
        geojson = geojson["features"][0]
    if geojson.get("type") == "Feature":
        geojson = geojson["geometry"]
    return geojson


def boundary_hash(geometry: dict[str, Any]) -> str:
    """A hash of the geometry itself, so reformatting the file does not change it."""
    canonical = json.dumps(geometry, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _metres_per_degree_lon(latitude: float) -> float:
    return _METRES_PER_DEGREE_LON_AT_EQUATOR * math.cos(math.radians(latitude))


def _circle(lon: float, lat: float, radius: float) -> list[list[float]]:
    # Circumscribed, so the polygon contains the whole circle.
    reach = radius / math.cos(math.pi / _CIRCLE_SEGMENTS)
    d_lon = reach / _metres_per_degree_lon(lat)
    d_lat = reach / _METRES_PER_DEGREE_LAT
    ring = [
        [
            lon + d_lon * math.cos(2 * math.pi * i / _CIRCLE_SEGMENTS),
            lat + d_lat * math.sin(2 * math.pi * i / _CIRCLE_SEGMENTS),
        ]
        for i in range(_CIRCLE_SEGMENTS)
    ]
    return [*ring, ring[0]]


def _band(a: list[float], b: list[float], radius: float) -> list[list[float]] | None:
    """The rectangle of points within `radius` of the segment a-b, off its ends excluded."""
    latitude = (a[1] + b[1]) / 2
    per_lon = _metres_per_degree_lon(latitude)
    dx = (b[0] - a[0]) * per_lon
    dy = (b[1] - a[1]) * _METRES_PER_DEGREE_LAT
    length = math.hypot(dx, dy)
    if length == 0:
        return None
    off_lon = -dy / length * radius / per_lon
    off_lat = dx / length * radius / _METRES_PER_DEGREE_LAT
    return [
        [a[0] + off_lon, a[1] + off_lat],
        [b[0] + off_lon, b[1] + off_lat],
        [b[0] - off_lon, b[1] - off_lat],
        [a[0] - off_lon, a[1] - off_lat],
        [a[0] + off_lon, a[1] + off_lat],
    ]


def buffered_region(geometry: dict[str, Any], radius: float = BUFFER_METRES) -> dict[str, Any]:
    """The boundary buffered by `radius` metres, as a MultiPolygon for `pmtiles --region`.

    The buffer is the union of each outer ring, a band along each edge, and a disc
    at each vertex; the parts overlap, which the extract's tile cover allows. Holes
    are filled: the extract may cover more than the boundary, never less.
    """
    polygons = (
        [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    )
    parts: list[list[list[list[float]]]] = []
    for polygon in polygons:
        ring = [[float(position[0]), float(position[1])] for position in polygon[0]]
        parts.append([ring])
        for a, b in pairwise(ring):
            band = _band(a, b, radius)
            if band is not None:
                parts.append([band])
        for lon, lat in ring[:-1]:
            parts.append([_circle(lon, lat, radius)])
    return {"type": "MultiPolygon", "coordinates": parts}


# The map styles


@dataclass(frozen=True)
class _StyleBasemap:
    uses_local: bool
    """Whether a style has a source at the symbolic local basemap URL."""
    schemas: frozenset[int]
    """The `metadata.tart:basemap-schema` values the styles declare."""


def _style_basemap(config_directory: Path) -> _StyleBasemap:
    uses_local = False
    schemas: set[int] = set()
    for file in STYLES:
        try:
            style = json.loads((config_directory / file).read_text(encoding="utf-8"))
        except OSError, ValueError:
            continue  # The configuration loader reports a missing or broken style.
        if not isinstance(style, dict):
            continue
        sources = style.get("sources")
        if isinstance(sources, dict) and any(
            isinstance(source, dict) and source.get("url") == SYMBOLIC_URL
            for source in sources.values()
        ):
            uses_local = True
        metadata = style.get("metadata")
        schema = metadata.get(SCHEMA_KEY) if isinstance(metadata, dict) else None
        if isinstance(schema, int) and not isinstance(schema, bool):
            schemas.add(schema)
    return _StyleBasemap(uses_local, frozenset(schemas))


def _declared_schema(config_directory: Path) -> int:
    schemas = _style_basemap(config_directory).schemas
    if not schemas:
        raise TilesError(
            f"the map styles declare no metadata.{SCHEMA_KEY}: set it to the Protomaps "
            "major the styles are written for"
        )
    if len(schemas) > 1:
        raise TilesError(
            f"the light and dark map styles declare different metadata.{SCHEMA_KEY} "
            f"values: {', '.join(map(str, sorted(schemas)))}"
        )
    return next(iter(schemas))


# PMTiles files


def basemap_version(path: Path) -> str | None:
    """The Protomaps basemap `version` in a PMTiles v3 file's metadata, or `None`."""
    try:
        with path.open("rb") as file:
            header = file.read(127)
            if len(header) < 127 or header[:7] != b"PMTiles" or header[7] != 3:
                return None
            offset = int.from_bytes(header[24:32], "little")
            length = int.from_bytes(header[32:40], "little")
            compression = header[97]
            file.seek(offset)
            raw = file.read(length)
        if compression == 2:
            raw = gzip.decompress(raw)
        elif compression != 1:
            return None
        version = json.loads(raw).get("version")
    except OSError, ValueError, AttributeError, EOFError:
        return None
    return version if isinstance(version, str) else None


def current_extract(tiles_directory: Path) -> Manifest | None:
    """The manifest of the current extract, or `None` when there is no usable extract."""
    try:
        data = json.loads((tiles_directory / MANIFEST).read_text(encoding="utf-8"))
        manifest = Manifest(**data)
    except OSError, ValueError, TypeError:
        return None
    if not _EXTRACT.match(manifest.file) or not (tiles_directory / manifest.file).is_file():
        return None
    return manifest


def _write_manifest(tiles_directory: Path, manifest: Manifest) -> None:
    partial = tiles_directory / (MANIFEST + _PARTIAL_SUFFIX)
    partial.write_text(json.dumps(asdict(manifest), indent=2) + "\n", encoding="utf-8")
    os.replace(partial, tiles_directory / MANIFEST)


# The command


def latest_build() -> str:
    """The date of the latest Protomaps daily build, from the builds list."""
    try:
        # The host refuses urllib's default User-Agent.
        request = urllib.request.Request(BUILDS_URL, headers={"User-Agent": "tart-tiles-update"})
        with urllib.request.urlopen(request, timeout=60) as response:
            builds = json.load(response)
        keys = [build["key"].removesuffix(".pmtiles") for build in builds]
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        raise TilesError(
            f"cannot read the list of Protomaps builds at {BUILDS_URL}: {error}"
        ) from error
    dates = [key for key in keys if is_build(key)]
    if not dates:
        raise TilesError(f"the list of Protomaps builds at {BUILDS_URL} names no build")
    return max(dates)


def _extract(source_url: str, region: dict[str, Any], output: Path) -> None:
    program = shutil.which(PMTILES_PROGRAM)
    if program is None:
        raise TilesError(f"the go-pmtiles program `{PMTILES_PROGRAM}` is not installed")
    with tempfile.TemporaryDirectory() as scratch:
        region_file = Path(scratch) / "region.geojson"
        region_file.write_text(json.dumps(region), encoding="utf-8")
        result = subprocess.run(
            [program, "extract", source_url, str(output), f"--region={region_file}"],
            check=False,
        )
    if result.returncode != 0 or not output.is_file():
        raise TilesError(f"the extraction from {source_url} failed")


def update(
    config_directory: Path,
    tiles_directory: Path,
    build: str | None = None,
    source: str | None = None,
) -> Manifest:
    """Extract, check, and swap in a new basemap; or raise `TilesError` or
    `ConfigurationError`, leaving the current extract in place."""
    load_instance(config_directory)  # The same validation as at startup.
    expected = _declared_schema(config_directory)
    geometry = boundary_geometry(config_directory)
    if build is None:
        if source is not None:
            raise TilesError("--source needs --build: the latest build is only known upstream")
        build = latest_build()
    if not is_build(build):
        raise TilesError(f"{build!r} is not a build date YYYYMMDD")
    source_url = f"{(source or DEFAULT_SOURCE).rstrip('/')}/{build}.pmtiles"

    tiles_directory.mkdir(parents=True, exist_ok=True)
    name = f"basemap-{build}.pmtiles"
    partial = tiles_directory / f".{name}{_PARTIAL_SUFFIX}"
    try:
        _extract(source_url, buffered_region(geometry), partial)
        version = basemap_version(partial)
        if version is None:
            raise TilesError(f"the extract from {source_url} has no Protomaps basemap version")
        if _major(version) != expected:
            raise TilesError(
                f"the extract from {source_url} has schema {version}, but the map styles "
                f"declare major {expected}: choose a build of that major with --build, or "
                f"update the styles and metadata.{SCHEMA_KEY}"
            )
        previous = current_extract(tiles_directory)
        os.replace(partial, tiles_directory / name)
    finally:
        partial.unlink(missing_ok=True)

    manifest = Manifest(name, build, version, boundary_hash(geometry))
    _write_manifest(tiles_directory, manifest)
    keep = {name, previous.file if previous else name}
    for path in tiles_directory.iterdir():
        if _EXTRACT.match(path.name) and path.name not in keep:
            path.unlink()
    return manifest


# Startup


def startup_warnings(config_directory: Path, tiles_directory: Path) -> list[str]:
    """What `api` logs at startup about the local basemap; never a reason to stop.

    Nothing applies when the styles do not use the local basemap (external tiles).
    """
    style = _style_basemap(config_directory)
    if not style.uses_local:
        return []
    manifest = current_extract(tiles_directory)
    if manifest is None:
        return [
            f"the basemap extract is missing from {tiles_directory}: the map will not "
            "appear until `tart tiles update` runs; the list and search work"
        ]
    warnings = []
    if manifest.boundary_sha256 != boundary_hash(boundary_geometry(config_directory)):
        warnings.append(
            f"the boundary changed since {manifest.file} was extracted: run `tart tiles update`"
        )
    mismatched = sorted(schema for schema in style.schemas if schema != manifest.schema_major)
    if mismatched:
        warnings.append(
            f"{manifest.file} has basemap schema {manifest.schema_version}, but the map "
            f"styles declare major {', '.join(map(str, mismatched))}: run `tart tiles update` "
            "with a build of that major"
        )
    return warnings
