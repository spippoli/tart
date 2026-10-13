"""Rome's configuration directory, the reference Instance (Foundations spec, Instance
configuration; Archive records spec, Instance configuration).

Rome's directory is the valid case of the loader with real values: it loads, passes
`tart config check`, and holds the values the specs set for Rome.
"""

import json
from itertools import pairwise
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tart.api.app import create_app
from tart.cli import main as run_cli
from tart.config import load_instance

ROME_CONFIG = Path(__file__).parents[2] / "instances" / "rome"

# Archive records spec, Instance configuration: the default Surface type list, in order.
DEFAULT_SURFACE_TYPES = [
    ("building_wall", "Muro di edificio", "Building wall"),
    ("boundary_wall", "Muro di cinta o di contenimento", "Boundary or retaining wall"),
    ("shutter", "Saracinesca", "Shutter"),
    ("door", "Porta o portone", "Door"),
    ("hoarding", "Recinzione di cantiere", "Construction hoarding"),
    ("fence", "Cancello o recinzione", "Gate or fence"),
    ("bridge_underpass", "Ponte, sottopasso, galleria", "Bridge, underpass, tunnel"),
    ("railway", "Infrastruttura ferroviaria", "Railway infrastructure"),
    (
        "street_furniture",
        "Arredo urbano (cabina, palo, cartello)",
        "Street furniture (cabinet, pole, sign)",
    ),
    ("ground", "Pavimentazione, scala", "Pavement, steps"),
    ("free_standing", "Struttura autonoma", "Free-standing structure"),
    ("other", "Altro", "Other"),
]


def _vocabulary(name: str) -> list[tuple[str, str, str]]:
    entries = load_instance(ROME_CONFIG).vocabularies[name]
    return [(entry.key, entry.label["it"], entry.label["en"]) for entry in entries]


def test_rome_config_check_succeeds(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Foundations criterion 1, the files part: `tart config check` passes on Rome."""
    monkeypatch.setenv("CONFIG_DIR", str(ROME_CONFIG))

    assert run_cli(["config", "check"]) == 0
    assert "the configuration is valid" in capsys.readouterr().out


def test_rome_api_starts_and_serves_its_public_configuration(
    database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Foundations criterion 1: with Rome's directory and a complete environment, `api` starts."""
    run_cli(["migrate"])
    monkeypatch.setenv("CONFIG_DIR", str(ROME_CONFIG))

    with TestClient(create_app()) as client:
        response = client.get("/api/config")

    assert response.status_code == 200
    assert response.json()["identity"]["name"] == "Archivio dell'arte urbana di Roma"


def test_ac52_a_new_instance_surface_type_file_holds_the_platform_default_list() -> None:
    """Archive records AC 52: the default list, in its order, with `it` and `en` labels."""
    assert _vocabulary("surface_types") == DEFAULT_SURFACE_TYPES
    entries = load_instance(ROME_CONFIG).vocabularies["surface_types"]
    assert not any(entry.retired or entry.description for entry in entries)


def test_rome_identity_languages_and_settings_are_romes_values() -> None:
    settings = load_instance(ROME_CONFIG).settings

    assert settings.identity.name == "Archivio dell'arte urbana di Roma"
    assert settings.identity.description.startswith("Un archivio collaborativo e moderato")
    assert settings.identity.logo.alt == "Archivio dell'arte urbana di Roma"
    assert (settings.identity.accent.light, settings.identity.accent.dark) == (
        "#7A2E1C",
        "#F0A08C",
    )
    assert settings.languages.content == "it"
    assert settings.languages.ui == ("it", "en")
    assert settings.geography.place_name == "Roma"
    assert settings.geography.time_zone == "Europe/Rome"
    assert settings.geography.default_view.center == (12.4823, 41.8955)
    assert settings.geography.default_view.zoom == 12
    assert settings.media.public_rendition_max_px == 2048
    assert settings.licenses.data == "CC-BY-SA-4.0"
    assert settings.licenses.files == ("CC-BY-SA-4.0", "CC-BY-4.0", "CC0-1.0")
    assert settings.community.registration == "open"
    assert settings.community.min_age == 14
    assert settings.terms.version == 1


def test_rome_launch_values_are_fictional_placeholders() -> None:
    """Foundations, Rome's launch values: placeholders until launch, on example.org."""
    settings = load_instance(ROME_CONFIG).settings

    contacts = settings.contacts
    assert all(
        address.endswith("@example.org")
        for address in (contacts.general, contacts.dsa, contacts.privacy)
    )
    assert contacts.dsa_languages == ("it", "en")
    assert "segnaposto" in settings.operator.name


def test_rome_operator_texts_are_marked_as_to_be_written() -> None:
    texts = load_instance(ROME_CONFIG).texts

    assert set(texts) == {
        "about",
        "editorial_guidelines",
        "contribution_policy",
        "terms",
        "privacy",
    }
    assert all(text and "Testo da scrivere" in text for text in texts.values())


def test_rome_expression_types_are_the_brief_list_plus_mosaic() -> None:
    assert [key for key, _, _ in _vocabulary("expression_types")] == [
        "mural",
        "graffiti",
        "stencil",
        "paste_up",
        "sticker",
        "mosaic",
        "installation",
        "temporary",
        "other",
    ]


def test_rome_decision_reasons_follow_the_checklist_then_duplicate() -> None:
    assert [key for key, _, _ in _vocabulary("decision_reasons")] == [
        "people",
        "file_rights",
        "attribution",
        "unlawful",
        "evidence",
        "location",
        "out_of_scope",
        "incomplete",
        "other",
        "duplicate",
    ]


def test_rome_notice_reasons_are_the_platform_default_keys_with_help() -> None:
    entries = load_instance(ROME_CONFIG).vocabularies["notice_reasons"]

    assert [entry.key for entry in entries] == [
        "artwork_copyright",
        "file_copyright",
        "personal_data",
        "illegal_content",
        "other",
    ]
    assert all(entry.description for entry in entries[:-1])


def _inside(point: tuple[float, float], geometry: dict) -> bool:
    """Even-odd ray casting over every ring of a Polygon or MultiPolygon."""
    polygons = (
        [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    )
    x, y = point
    inside = False
    for ring in (ring for polygon in polygons for ring in polygon):
        for (x1, y1), (x2, y2) in pairwise(ring):
            if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                inside = not inside
    return inside


def test_rome_boundary_is_roma_capitale_with_vatican_city_from_openstreetmap() -> None:
    boundary = json.loads((ROME_CONFIG / "geography" / "boundary.geojson").read_text())
    west, south, east, north = load_instance(ROME_CONFIG).bounds

    assert boundary["properties"]["license"] == "ODbL-1.0"
    assert boundary["properties"]["attribution"] == "© OpenStreetMap contributors"
    # Roma Capitale reaches Ostia on the coast, and its northern exclave past 42.1° N.
    assert 12.2 < west < 12.3 and 12.8 < east < 12.9
    assert 41.6 < south < 41.7 and 42.1 < north < 42.2
    centre = load_instance(ROME_CONFIG).settings.geography.default_view.center
    assert _inside(centre, boundary["geometry"])
    # St Peter's Basilica, in Vatican City: the hole is filled.
    assert _inside((12.4534, 41.9022), boundary["geometry"])
    # Fiumicino's airport, a separate municipality, stays outside.
    assert not _inside((12.2389, 41.8003), boundary["geometry"])


def test_rome_overlay_holds_the_walls_and_archaeology_from_openstreetmap() -> None:
    """Discovery spec, Overlays: walls, archaeological sites, and ruins, under the ODbL."""
    overlay = json.loads((ROME_CONFIG / "map" / "overlay.geojson").read_text())
    names = {feature["properties"].get("name") for feature in overlay["features"]}

    assert {feature["properties"]["kind"] for feature in overlay["features"]} == {"wall", "ruin"}
    assert {"Mura Aureliane", "Mura Serviane"} <= names
    assert all(feature["geometry"]["type"] != "Point" for feature in overlay["features"])
    readme = (ROME_CONFIG / "map" / "README.md").read_text()
    assert "© OpenStreetMap contributors" in readme and "Open Database License" in readme
    assert (ROME_CONFIG / "map" / "overlay.overpassql").is_file()


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_rome_style_draws_the_overlay_below_the_archive_layers(theme: str) -> None:
    """Discovery spec, Overlays: drawn by the Instance style, below the archive layers."""
    style = json.loads((ROME_CONFIG / "map" / f"style.{theme}.json").read_text())
    ids = [layer["id"] for layer in style["layers"]]
    below = ids.index(style["metadata"]["tart:insert-archive-below"])
    overlay = [
        index
        for index, layer in enumerate(style["layers"])
        if layer.get("source") == "overlay" and layer["type"] == "line"
    ]

    assert style["sources"]["overlay"] == {"type": "geojson", "data": "/map/overlay.geojson"}
    assert overlay and all(index < below for index in overlay)
    # The walls are a heavy ink line; labels are Goudy, served as font files.
    walls = next(layer for layer in style["layers"] if layer["id"] == "overlay-walls")
    assert walls["paint"]["line-color"] == style["metadata"]["tart:tokens"]["map.ink"]
    fonts = {
        font for layer in style["layers"] for font in layer.get("layout", {}).get("text-font", [])
    }
    assert fonts <= set(style["font-faces"])
