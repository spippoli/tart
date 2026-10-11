"""Discovery spec, Map style ownership and serving: the style rules and the style endpoint.

The rules run through the configuration loader (startup) and `tart config check`,
with one failure fixture per rule under `fixtures/config/failures`, laid over the
valid configuration as the Foundations fixtures are. The endpoint is driven through
the HTTP API with a PMTiles directory per test.
"""

import json
from pathlib import Path

import pytest
from conftest import ENVIRONMENT, VALID_CONFIG, config_fixture
from fastapi.testclient import TestClient

from tart.api.app import create_app
from tart.api.map_style import get_configuration
from tart.cli import main as run_cli
from tart.colour import parse_colour
from tart.config import ConfigurationError, load_configuration, load_instance
from tart.config.public import public_configuration

LIGHT = "map/style.light.json"
DARK = "map/style.dark.json"
BASE_URL = ENVIRONMENT["PUBLIC_BASE_URL"]

# Fixture name -> the (file, key) of every issue it must produce, and nothing else.
STYLE_FAILURES = {
    # Foundations criterion 5.
    "missing_dark_style": [(DARK, "")],
    "style_parity": [(DARK, "sources"), (DARK, "layers"), (DARK, "layers")],
    "missing_insertion_layer": [(LIGHT, "metadata.tart:insert-archive-below")],
    "line_dasharray": [(LIGHT, "layers[4].paint.line-dasharray")],
    "missing_asset": [(LIGHT, "sprite"), (DARK, "sprite")],
    # Discovery criterion 63.
    "missing_tokens": [
        (LIGHT, "metadata.tart:tokens.map.paper"),
        (LIGHT, "metadata.tart:tokens.map.ink"),
        (LIGHT, "metadata.tart:tokens.marker.ink"),
        (LIGHT, "metadata.tart:tokens.map.label.district"),
    ],
    "accent_token": [(LIGHT, "metadata.tart:tokens.marker.accent")],
    "missing_noto_sans": [(LIGHT, "glyphs"), (DARK, "glyphs")],
    "missing_goudy_font": [(LIGHT, "glyphs")],
    # Discovery criterion 44: the other rules.
    "missing_insertion_metadata": [(LIGHT, "metadata.tart:insert-archive-below")],
    "missing_basemap_schema": [(LIGHT, "metadata.tart:basemap-schema")],
    "patterns": [(LIGHT, "layers[3].paint.fill-pattern"), (LIGHT, "layers[5].paint.line-pattern")],
    "asset_not_root_relative": [(LIGHT, "sprite")],
    "non_https_source": [(LIGHT, "sources.basemap.url")],
    "low_contrast_fill": [(LIGHT, "layers[1].paint.fill-color")] * 2,
    "non_literal_fill": [(LIGHT, "layers[1].paint.fill-color")],
    "low_label_contrast": [(LIGHT, "layers[6].paint.text-color")],
    "missing_label_halo": [(LIGHT, "layers[6].paint.text-halo-color")],
    # Foundations criterion 4: the accent against the map fills.
    "low_contrast_accent_map_fill": [
        (LIGHT, "layers[0].paint.background-color"),
        (LIGHT, "layers[1].paint.fill-color"),
        (LIGHT, "layers[2].paint.fill-color"),
        (LIGHT, "layers[2].paint.fill-color"),
        (LIGHT, "layers[3].paint.fill-color"),
        (LIGHT, "layers[3].paint.fill-color"),
    ],
}

SEVERAL_STYLE_ERRORS = [
    (LIGHT, "metadata.tart:tokens.map.label.district"),
    (LIGHT, "sources.basemap.url"),
    (LIGHT, "layers[4].paint.line-dasharray"),
    (DARK, "metadata.tart:insert-archive-below"),
]


def _issues(directory: Path) -> list[tuple[str, str]]:
    with pytest.raises(ConfigurationError) as raised:
        load_instance(directory)
    return [(issue.file, issue.key) for issue in raised.value.issues]


def _check(directory: Path, monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.setenv("CONFIG_DIR", str(directory))
    return run_cli(["config", "check"])


def test_criterion_44_the_valid_styles_pass_in_both_themes() -> None:
    instance = load_instance(VALID_CONFIG)

    assert set(instance.map_styles) == {"light", "dark"}
    assert instance.map_styles["light"]["metadata"]["tart:insert-archive-below"] == "street-labels"


@pytest.mark.parametrize("name", STYLE_FAILURES)
def test_criteria_44_63_and_foundations_4_5_each_rule_fails_validation(
    name: str, tmp_path: Path
) -> None:
    assert _issues(config_fixture(name, tmp_path)) == STYLE_FAILURES[name]


@pytest.mark.parametrize("name", STYLE_FAILURES)
def test_criteria_44_63_and_foundations_5_config_check_fails_on_each_rule(
    name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = _check(config_fixture(name, tmp_path), monkeypatch)

    assert status == 1
    errors = capsys.readouterr().err
    for file, key in STYLE_FAILURES[name]:
        assert (f"{file}: {key}:" if key else f"{file}:") in errors


def test_criterion_44_startup_and_config_check_report_every_style_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    directory = config_fixture("several_style_errors", tmp_path)

    # Startup loads the configuration with load_configuration, which stops on any error.
    with pytest.raises(ConfigurationError) as raised:
        load_configuration(directory, {**ENVIRONMENT, "DATABASE_URL": "postgresql+asyncpg://x"})
    status = _check(directory, monkeypatch)

    assert [(issue.file, issue.key) for issue in raised.value.issues] == SEVERAL_STYLE_ERRORS
    assert status == 1
    assert capsys.readouterr().err.strip() == str(raised.value).strip()


def test_criterion_44_an_overlay_over_1_mb_fails_validation(tmp_path: Path) -> None:
    directory = config_fixture("no_general_contact", tmp_path)
    overlay = directory / "map" / "overlays" / "walls.geojson"
    features = [
        {
            "type": "Feature",
            "properties": {"n": n},
            "geometry": {"type": "Point", "coordinates": [12.4, 41.9]},
        }
        for n in range(15_000)
    ]
    overlay.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    assert overlay.stat().st_size > 1024 * 1024

    assert _issues(directory) == [(LIGHT, "sources.walls.data"), (DARK, "sources.walls.data")]


def test_criterion_63_the_messages_name_the_rule(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError) as raised:
        load_instance(config_fixture("accent_token", tmp_path))

    (issue,) = raised.value.issues
    assert "instance.toml" in issue.message


@pytest.mark.parametrize(
    ("literal", "expected"),
    [
        ("#F3EEE2", ("#F3EEE2", 1.0)),
        ("#abc", ("#AABBCC", 1.0)),
        ("#11223380", ("#112233", 128 / 255)),
        ("rgb(255, 0, 0)", ("#FF0000", 1.0)),
        ("rgba(0 0 255 / 50%)", ("#0000FF", 0.5)),
        ("hsl(0, 100%, 50%)", ("#FF0000", 1.0)),
        ("DarkSlateGray", ("#2F4F4F", 1.0)),
        ("transparent", ("#000000", 0.0)),
        ("not-a-colour", None),
        ("rgb(1, 2)", None),
    ],
)
def test_criterion_44_colour_literals_are_read_as_maplibre_reads_them(
    literal: str, expected: tuple[str, float] | None
) -> None:
    assert parse_colour(literal) == expected


# The endpoint (criteria 45 and 70).


def _client(directory: Path, tiles: Path) -> TestClient:
    configuration = load_configuration(
        directory,
        {**ENVIRONMENT, "DATABASE_URL": "postgresql+asyncpg://x", "PMTILES_PATH": str(tiles)},
    )
    app = create_app()
    app.dependency_overrides[get_configuration] = lambda: configuration
    return TestClient(app)


def _extract(tiles: Path, build: str) -> str:
    """What `tart tiles update` leaves: a versioned extract named by the manifest."""
    name = f"basemap-{build}.pmtiles"
    (tiles / name).write_bytes(b"PMTiles fixture")
    (tiles / "manifest.json").write_text(json.dumps({"file": name, "build": build}))
    return name


def test_criterion_45_the_served_style_has_absolute_asset_urls_and_the_current_extract(
    tmp_path: Path,
) -> None:
    extract = _extract(tmp_path, "20261001")

    response = _client(VALID_CONFIG, tmp_path).get("/api/map/style/light.json")

    assert response.status_code == 200
    style = response.json()
    assert style["glyphs"] == f"{BASE_URL}/map/glyphs/{{fontstack}}/{{range}}.pbf"
    assert style["sprite"] == f"{BASE_URL}/map/sprites/basemap"
    assert style["font-faces"]["Sorts Mill Goudy Regular"] == (
        f"{BASE_URL}/map/fonts/SortsMillGoudy-Regular.ttf"
    )
    assert style["font-faces"]["Sorts Mill Goudy Small Caps"][0]["url"] == (
        f"{BASE_URL}/map/fonts/SortsMillGoudy-Regular.ttf"
    )
    assert style["sources"]["walls"]["data"] == f"{BASE_URL}/map/overlays/walls.geojson"
    assert style["sources"]["basemap"]["url"] == f"pmtiles://{BASE_URL}/tiles/{extract}"
    assert "pmtiles:///tiles/basemap.pmtiles" not in response.text


def test_the_served_style_supplies_the_insertion_point_and_tokens_with_the_theme_accent(
    tmp_path: Path,
) -> None:
    _extract(tmp_path, "20261001")
    client = _client(VALID_CONFIG, tmp_path)

    light = client.get("/api/map/style/light.json").json()["metadata"]
    dark = client.get("/api/map/style/dark.json").json()["metadata"]

    assert light["tart:insert-archive-below"] == "street-labels"
    assert light["tart:tokens"]["marker.ink"] == "#1F1B18"
    assert light["tart:tokens"]["marker.accent"] == "#7A2E1C"
    assert dark["tart:tokens"]["marker.ink"] == "#F6F0E6"
    assert dark["tart:tokens"]["marker.accent"] == "#F0A08C"
    # The configuration as loaded is never changed by serving.
    assert (
        "marker.accent"
        not in load_instance(VALID_CONFIG).map_styles["light"]["metadata"]["tart:tokens"]
    )


def test_criterion_70_the_style_is_no_cache_with_an_etag_and_answers_304(tmp_path: Path) -> None:
    _extract(tmp_path, "20261001")
    client = _client(VALID_CONFIG, tmp_path)

    first = client.get("/api/map/style/dark.json")
    repeat = client.get(
        "/api/map/style/dark.json", headers={"If-None-Match": first.headers["ETag"]}
    )

    assert first.status_code == 200
    assert first.headers["Cache-Control"] == "no-cache"
    assert first.headers["ETag"].startswith('"')
    assert repeat.status_code == 304
    assert repeat.content == b""
    assert repeat.headers["ETag"] == first.headers["ETag"]


def test_criterion_70_the_etag_changes_after_tart_tiles_update(tmp_path: Path) -> None:
    _extract(tmp_path, "20261001")
    client = _client(VALID_CONFIG, tmp_path)
    before = client.get("/api/map/style/light.json")

    extract = _extract(tmp_path, "20270401")
    after = client.get(
        "/api/map/style/light.json", headers={"If-None-Match": before.headers["ETag"]}
    )

    assert after.status_code == 200
    assert after.headers["ETag"] != before.headers["ETag"]
    assert after.json()["sources"]["basemap"]["url"].endswith(f"/tiles/{extract}")


@pytest.mark.parametrize(
    "manifest",
    [
        None,
        {"file": "basemap-20261001.pmtiles"},  # The manifest names a file that is gone.
        {"file": "../secrets.pmtiles"},
    ],
)
def test_criterion_70_without_an_extract_the_style_answers_503_tiles_missing(
    tmp_path: Path, manifest: dict[str, str] | None
) -> None:
    if manifest is not None:
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))

    response = _client(VALID_CONFIG, tmp_path).get("/api/map/style/light.json")

    assert response.status_code == 503
    assert response.json() == {"code": "tiles_missing"}
    assert response.headers["Cache-Control"] == "no-cache"


def test_criterion_70_a_style_with_only_external_tiles_needs_no_extract(tmp_path: Path) -> None:
    directory = config_fixture("external_tiles", tmp_path / "config")
    tiles = tmp_path / "tiles"
    tiles.mkdir()

    response = _client(directory, tiles).get("/api/map/style/light.json")

    assert response.status_code == 200
    assert response.json()["sources"]["basemap"]["url"] == (
        "pmtiles://https://tiles.example.org/fictional-city.pmtiles"
    )


def test_an_unknown_theme_is_not_served(tmp_path: Path) -> None:
    _extract(tmp_path, "20261001")

    response = _client(VALID_CONFIG, tmp_path).get("/api/map/style/sepia.json")

    assert response.status_code == 422


# Content-Security-Policy (criterion 48): the API names the external origins, which the
# frontend adds to the policy of its pages.


def test_criterion_48_external_https_tile_origins_are_public(tmp_path: Path) -> None:
    external = load_instance(config_fixture("external_tiles", tmp_path))

    assert public_configuration(external).map_tile_origins == [
        "https://raster.example.net:8443",
        "https://tiles.example.org",
    ]
    assert public_configuration(load_instance(VALID_CONFIG)).map_tile_origins == []
