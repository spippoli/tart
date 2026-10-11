"""Load the configuration directory and the environment, or list every error.

    load_configuration(directory, environ) -> Configuration   # or ConfigurationError

Every path in the directory is fixed by the platform. Validation never stops at the
first error: each file is read and checked, and `ConfigurationError.issues` holds
all that is wrong, each with the file and the dotted key it concerns.
"""

import json
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from pydantic import BaseModel, ValidationError

from tart.colour import HEX_COLOUR, contrast_ratio
from tart.config.environment import Environment
from tart.config.instance import (
    ACCENT_MIN_CONTRAST,
    BOUNDARY,
    DARK_BACKGROUND,
    FAVICON,
    LIGHT_BACKGROUND,
    LOGO_DARK,
    LOGO_LIGHT,
    InstanceFile,
)
from tart.config.vocabularies import VOCABULARIES, Entry, VocabularyFile, duplicate_entry
from tart.map.style import THEMES, read_styles
from tart.messages import UI_LANGUAGES

INSTANCE_FILE = "instance.toml"
REQUIRED_TEXTS = ("terms", "privacy")
OPTIONAL_TEXTS = ("about", "editorial_guidelines", "contribution_policy")
ENVIRONMENT = "environment"
"""The `file` of an issue about an environment variable."""


@dataclass(frozen=True)
class Issue:
    file: str
    """A path relative to the configuration directory, or `environment`."""
    key: str
    """The dotted key within the file (`identity.accent.dark`), or `""` for the whole file."""
    message: str

    def __str__(self) -> str:
        where = f"{self.file}: {self.key}" if self.key else self.file
        return f"{where}: {self.message}"


class ConfigurationError(Exception):
    def __init__(self, issues: list[Issue]) -> None:
        self.issues = issues
        lines = "\n".join(f"  {issue}" for issue in issues)
        super().__init__(f"invalid configuration, {len(issues)} error(s):\n{lines}")


@dataclass(frozen=True)
class Identity:
    """The identity files' SVG sources."""

    logo_light: str
    logo_dark: str
    favicon: str


@dataclass(frozen=True)
class Instance:
    """What the configuration directory says the archive is."""

    settings: InstanceFile
    vocabularies: Mapping[str, tuple[Entry, ...]]
    """By vocabulary name, in display order; `decision_reasons` ends with `duplicate`."""
    texts: Mapping[str, str | None]
    """The Operator texts' Markdown by name; an optional text may be `None`."""
    identity: Identity
    bounds: tuple[float, float, float, float]
    """The boundary's bounding box: west, south, east, north."""
    boundary: Mapping[str, Any]
    """The boundary as a GeoJSON Polygon or MultiPolygon geometry."""
    map_styles: Mapping[str, Mapping[str, Any]]
    """The validated map style files by theme (`light`, `dark`), as read; never modified."""


@dataclass(frozen=True)
class Configuration:
    instance: Instance
    environment: Environment


def _location(loc: tuple[int | str, ...]) -> str:
    key = ""
    for part in loc:
        key += f"[{part}]" if isinstance(part, int) else f".{part}" if key else str(part)
    return key


def _validate[M: BaseModel](
    model: type[M], data: object, file: str, issues: list[Issue], context: dict | None = None
) -> M | None:
    try:
        return model.model_validate(data, context=context)
    except ValidationError as error:
        for detail in error.errors():
            message = detail["msg"].removeprefix("Value error, ")
            if detail["type"] == "missing":
                message = "is required"
            elif detail["type"] == "extra_forbidden":
                message = "is not a known key"
            elif detail["type"] == "too_short" and detail.get("ctx", {}).get("min_length") == 1:
                message = "must not be empty"
            issues.append(Issue(file, _location(detail["loc"]), message))
        return None


def _read_toml(directory: Path, file: str, issues: list[Issue]) -> dict[str, Any] | None:
    path = directory / file
    if not path.is_file():
        issues.append(Issue(file, "", "is missing"))
        return None
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as error:
        issues.append(Issue(file, "", f"is not valid TOML: {error}"))
        return None


def _read_text(directory: Path, file: str, issues: list[Issue], *, required: bool) -> str | None:
    path = directory / file
    if not path.is_file():
        if required:
            issues.append(Issue(file, "", "is missing"))
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        issues.append(Issue(file, "", "is not UTF-8 text"))
        return None
    if required and not text.strip():
        issues.append(Issue(file, "", "is empty"))
    return text


def _read_svg(directory: Path, file: str, issues: list[Issue]) -> str:
    text = _read_text(directory, file, issues, required=True)
    if text is None:
        return ""
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as error:
        issues.append(Issue(file, "", f"is not well-formed XML: {error}"))
        return ""
    if root.tag not in ("svg", "{http://www.w3.org/2000/svg}svg"):
        issues.append(Issue(file, "", "is not an SVG image"))
    return text


def _positions(geometry: dict[str, Any]) -> list[list[float]]:
    rings = geometry["coordinates"]
    polygons = [rings] if geometry["type"] == "Polygon" else rings
    return [position for polygon in polygons for ring in polygon for position in ring]


def _read_boundary(
    directory: Path, issues: list[Issue]
) -> tuple[dict[str, Any], tuple[float, float, float, float]] | None:
    """The boundary geometry and its bounding box."""
    text = _read_text(directory, BOUNDARY, issues, required=True)
    if text is None:
        return None
    try:
        geojson = json.loads(text)
        if geojson.get("type") == "FeatureCollection" and len(geojson["features"]) == 1:
            geojson = geojson["features"][0]
        if geojson.get("type") == "Feature":
            geojson = geojson["geometry"]
        if geojson.get("type") not in ("Polygon", "MultiPolygon"):
            raise ValueError
        positions = _positions(geojson)
        longitudes = [float(position[0]) for position in positions]
        latitudes = [float(position[1]) for position in positions]
    except ValueError, KeyError, TypeError, IndexError, AttributeError:
        issues.append(
            Issue(
                BOUNDARY,
                "",
                "must hold one Polygon or MultiPolygon, as a geometry, a Feature, "
                "or a FeatureCollection of one Feature",
            )
        )
        return None
    return geojson, (min(longitudes), min(latitudes), max(longitudes), max(latitudes))


def _enabled_ui_languages(raw: dict[str, Any] | None) -> tuple[str, ...]:
    """The enabled UI languages the platform has, read leniently for the label checks."""
    ui = ((raw or {}).get("languages") or {}).get("ui")
    if not isinstance(ui, list):
        return ()
    return tuple(language for language in ui if language in UI_LANGUAGES)


def _accents(raw: dict[str, Any] | None) -> dict[str, str | None]:
    """The accent of each theme for the map style checks, read leniently.

    An accent that fails its own check (not a colour, or too close to its theme's UI
    background) is reported with `instance.toml` alone, and left out of the map checks.
    """
    accent = ((raw or {}).get("identity") or {}).get("accent")
    accent = accent if isinstance(accent, dict) else {}
    accents: dict[str, str | None] = {}
    for theme in THEMES:
        value = accent.get(theme)
        valid = isinstance(value, str) and HEX_COLOUR.match(value) is not None
        background = LIGHT_BACKGROUND if theme == "light" else DARK_BACKGROUND
        if valid and contrast_ratio(value, background) >= ACCENT_MIN_CONTRAST:
            accents[theme] = value.upper()
        else:
            accents[theme] = None
    return accents


def load_instance(directory: Path) -> Instance:
    """Read and validate the configuration directory, or raise `ConfigurationError`."""
    issues: list[Issue] = []

    raw = _read_toml(directory, INSTANCE_FILE, issues)
    settings = _validate(InstanceFile, raw, INSTANCE_FILE, issues) if raw is not None else None

    context = {"ui_languages": _enabled_ui_languages(raw)}
    vocabularies: dict[str, tuple[Entry, ...]] = {}
    for name in VOCABULARIES:
        file = f"vocabularies/{name}.toml"
        data = _read_toml(directory, file, issues)
        if data is not None:
            vocabulary = _validate(VocabularyFile, data, file, issues, context)
            if vocabulary is not None:
                vocabularies[name] = vocabulary.entries
    if "decision_reasons" in vocabularies:
        vocabularies["decision_reasons"] += (duplicate_entry(),)

    texts = {
        name: _read_text(directory, f"texts/{name}.md", issues, required=name in REQUIRED_TEXTS)
        for name in (*OPTIONAL_TEXTS, *REQUIRED_TEXTS)
    }
    identity = Identity(
        logo_light=_read_svg(directory, LOGO_LIGHT, issues),
        logo_dark=_read_svg(directory, LOGO_DARK, issues),
        favicon=_read_svg(directory, FAVICON, issues),
    )
    boundary = _read_boundary(directory, issues)
    map_styles, style_issues = read_styles(directory, _accents(raw))
    issues += [Issue(file, key, message) for file, key, message in style_issues]

    if issues:
        raise ConfigurationError(issues)
    assert settings is not None and boundary is not None
    geometry, bounds = boundary
    return Instance(settings, vocabularies, texts, identity, bounds, geometry, map_styles)


def load_environment(environ: Mapping[str, str]) -> Environment:
    """Read the environment variables, or raise `ConfigurationError`."""
    issues: list[Issue] = []
    # An empty variable, as Compose passes an unset `${NAME:-}`, counts as unset.
    present = {name: value for name, value in environ.items() if value}
    environment = _validate(Environment, present, ENVIRONMENT, issues)
    if issues:
        raise ConfigurationError(issues)
    assert environment is not None
    return environment


def load_configuration(directory: Path, environ: Mapping[str, str]) -> Configuration:
    """Load the directory and the environment; every error of both is reported together."""
    issues: list[Issue] = []
    instance = environment = None
    try:
        instance = load_instance(directory)
    except ConfigurationError as error:
        issues += error.issues
    try:
        environment = load_environment(environ)
    except ConfigurationError as error:
        issues += error.issues
    if issues:
        raise ConfigurationError(issues)
    assert instance is not None and environment is not None
    return Configuration(instance, environment)
