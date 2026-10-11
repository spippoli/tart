"""The rules of the Instance's map styles (Discovery spec, Map style ownership and serving).

    read_styles(directory, accents) -> (styles by theme, issues)

The Instance ships two finished MapLibre styles at fixed paths. The platform checks
here, in Python, only TART's own rules; full style-spec conformance is left to
`gl-style-validate` in CI, so the `api` image needs no Node. Every rule is checked
and every failure reported, each with the style file and the dotted key it concerns.
"""

import json
import re
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from tart.colour import contrast_ratio, parse_colour

THEMES = ("light", "dark")
STYLE_FILES = {theme: f"map/style.{theme}.json" for theme in THEMES}

ASSET_PREFIX = "/map/"
"""The one known prefix of root-relative asset paths, served from the directory's `map/`."""

BASEMAP_URL = "pmtiles:///tiles/basemap.pmtiles"
"""The symbolic URL of the local basemap, rewritten to the current extract when served."""

INSERT_BELOW = "tart:insert-archive-below"
TOKENS = "tart:tokens"
BASEMAP_SCHEMA = "tart:basemap-schema"

REQUIRED_TOKENS = ("map.paper", "map.ink", "marker.ink", "map.label.district")
"""The closed list of colours the archive layers read from the style."""
ACCENT_TOKEN = "marker.accent"
"""Set by the platform from `instance.toml` when serving; an error in a style file."""

FONTS = (
    "Sorts Mill Goudy Regular",
    "Sorts Mill Goudy Italic",
    "Sorts Mill Goudy Small Caps",
    "Noto Sans Regular",
)
"""The font names the archive layers use: Goudy for district and Site labels (small caps
for Site labels), Noto Sans for cluster counts and as the glyph fallback."""
GLYPH_RANGE = "0-255"
"""The glyph range whose file must exist for a font served as glyphs."""

BANNED_PROPERTIES = ("line-dasharray", "fill-pattern", "line-pattern")
"""Dashes and patterns are reserved for TART's signs (ADR 0017)."""

OVERLAY_MAX_BYTES = 1024 * 1024
FILL_MIN_CONTRAST = 3.0
TEXT_MIN_CONTRAST = 4.5

_INTERPOLATE = ("interpolate", "interpolate-hcl", "interpolate-lab")


class _Issues:
    """Collects the issues of one style file as (key, message) pairs."""

    def __init__(self) -> None:
        self.items: list[tuple[str, str]] = []

    def add(self, key: str, message: str) -> None:
        self.items.append((key, message))


def _outputs(value: Any) -> Iterator[Any] | None:
    """The values a colour property can take, or `None` if one is not a literal.

    A literal, or an expression (or legacy function) whose every output is a literal:
    `interpolate`, `step`, `case`, `match`, `coalesce`, and `literal`.
    """
    if isinstance(value, str):
        return iter([value])
    if isinstance(value, dict) and isinstance(value.get("stops"), list):
        branches = [stop[1] for stop in value["stops"] if isinstance(stop, list) and len(stop) == 2]
        if "default" in value:
            branches.append(value["default"])
    elif isinstance(value, list) and value and isinstance(value[0], str):
        operator, arguments = value[0], value[1:]
        if operator == "literal" and len(arguments) == 1:
            branches = arguments
        elif operator in _INTERPOLATE and len(arguments) >= 4:
            branches = arguments[3::2]
        elif operator == "step" and len(arguments) >= 2:
            branches = [arguments[1], *arguments[3::2]]
        elif operator == "case" and len(arguments) >= 1:
            branches = [*arguments[1:-1:2], arguments[-1]]
        elif operator == "match" and len(arguments) >= 2:
            branches = [*arguments[2:-1:2], arguments[-1]]
        elif operator == "coalesce":
            branches = arguments
        else:
            return None
    else:
        return None
    outputs: list[Any] = []
    for branch in branches:
        inner = _outputs(branch)
        if inner is None:
            return None
        outputs += inner
    return iter(outputs)


def _colours(value: Any, key: str, issues: _Issues, *, opaque: bool = False) -> list[str] | None:
    """The `#RRGGBB` colours a property can take; `None` after reporting an issue.

    A fully transparent colour draws nothing and is left out; a translucent one is
    checked as if it were opaque. With `opaque`, any colour that is not fully opaque is
    an issue: what shows through it is unknown, so no contrast can be checked against it.
    """
    try:
        outputs = _outputs(value)
    except RecursionError:
        issues.add(key, "is nested too deeply")
        return None
    if outputs is None:
        issues.add(
            key,
            "must be a colour literal, or an expression whose every output is a colour "
            "literal (interpolate, step, case, match, coalesce), so that its contrast "
            "can be checked",
        )
        return None
    colours = []
    for output in outputs:
        parsed = parse_colour(output) if isinstance(output, str) else None
        if parsed is None:
            issues.add(key, f"{json.dumps(output)} is not a colour")
            return None
        colour, alpha = parsed
        if opaque and alpha < 1:
            issues.add(key, f"{json.dumps(output)} must be opaque, so that contrast can be checked")
            return None
        if alpha > 0:
            colours.append(colour)
    return colours


def _asset_file(directory: Path, path: str, key: str, issues: _Issues) -> Path | None:
    """The file a root-relative asset path points to, or `None` after reporting an issue."""
    if not path.startswith(ASSET_PREFIX):
        issues.add(
            key,
            f"{path!r} must be a root-relative path under {ASSET_PREFIX}, "
            "for a file in the configuration directory's map/",
        )
        return None
    root = (directory / "map").resolve()
    file = (directory / path.removeprefix("/")).resolve()
    if not file.is_relative_to(root):
        issues.add(key, f"{path!r} leaves the configuration directory's map/")
        return None
    return file


def _check_file(directory: Path, path: str, key: str, issues: _Issues) -> Path | None:
    file = _asset_file(directory, path, key, issues)
    if file is None:
        return None
    if not file.is_file():
        issues.add(key, f"{path} does not exist in the configuration directory")
        return None
    return file


def _font_face_urls(face: Any) -> list[Any]:
    if isinstance(face, list):
        return [entry.get("url") if isinstance(entry, dict) else None for entry in face]
    return [face]


def _check_metadata(style: dict[str, Any], issues: _Issues) -> None:
    metadata = style.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    layer_ids = [layer.get("id") for layer in _layers(style)]
    insert_below = metadata.get(INSERT_BELOW)
    if insert_below is None:
        issues.add(f"metadata.{INSERT_BELOW}", "is required")
    elif insert_below not in layer_ids:
        issues.add(
            f"metadata.{INSERT_BELOW}",
            f"names the layer {json.dumps(insert_below)}, which the style does not have",
        )

    tokens = metadata.get(TOKENS)
    if not isinstance(tokens, dict):
        issues.add(f"metadata.{TOKENS}", "is required, as an object of colours")
    else:
        for token in REQUIRED_TOKENS:
            if token not in tokens:
                issues.add(f"metadata.{TOKENS}.{token}", "is required")
            elif not isinstance(tokens[token], str) or parse_colour(tokens[token]) is None:
                issues.add(f"metadata.{TOKENS}.{token}", "must be a colour")
        if ACCENT_TOKEN in tokens:
            issues.add(
                f"metadata.{TOKENS}.{ACCENT_TOKEN}",
                "must not be set: the accent comes from instance.toml (identity.accent)",
            )

    schema = metadata.get(BASEMAP_SCHEMA)
    if uses_basemap(style) and schema is None:
        issues.add(f"metadata.{BASEMAP_SCHEMA}", f"is required when a source uses {BASEMAP_URL}")
    elif schema is not None and (not isinstance(schema, int) or isinstance(schema, bool)):
        issues.add(f"metadata.{BASEMAP_SCHEMA}", "must be the Protomaps schema major, an integer")


def _check_fonts(directory: Path, style: dict[str, Any], issues: _Issues) -> None:
    font_faces = style.get("font-faces")
    if not isinstance(font_faces, dict):
        font_faces = {}
    glyphs = style.get("glyphs")
    for font in FONTS:
        if font in font_faces:
            continue  # Its files are checked with the other assets.
        if isinstance(glyphs, str) and glyphs.startswith(ASSET_PREFIX):
            path = glyphs.replace("{fontstack}", font).replace("{range}", GLYPH_RANGE)
            if (directory / path.removeprefix("/")).is_file():
                continue
        issues.add(
            "glyphs",
            f"has no {font}: the platform's labels need it, as a font-faces entry or as "
            f"glyphs under {ASSET_PREFIX}",
        )


def _check_assets(directory: Path, style: dict[str, Any], issues: _Issues) -> None:
    glyphs = style.get("glyphs")
    if glyphs is not None:
        if not isinstance(glyphs, str):
            issues.add("glyphs", "must be a URL template")
        else:
            _asset_file(directory, glyphs, "glyphs", issues)

    sprite = style.get("sprite")
    sprites = (
        [("sprite", sprite)]
        if isinstance(sprite, str)
        else [
            (f"sprite[{index}].url", entry.get("url") if isinstance(entry, dict) else None)
            for index, entry in enumerate(sprite)
        ]
        if isinstance(sprite, list)
        else []
    )
    for key, url in sprites:
        if not isinstance(url, str):
            issues.add(key, "must be a URL")
            continue
        base = _asset_file(directory, url, key, issues)
        if base is None:
            continue
        for extension in (".json", ".png"):
            if not base.with_name(base.name + extension).is_file():
                issues.add(key, f"{url}{extension} does not exist in the configuration directory")

    font_faces = style.get("font-faces")
    if isinstance(font_faces, dict):
        for font, face in font_faces.items():
            for url in _font_face_urls(face):
                key = f"font-faces.{font}"
                if isinstance(url, str):
                    _check_file(directory, url, key, issues)
                else:
                    issues.add(key, "must be a URL or a list of {url, unicode-range}")


def _source_urls(style: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """Every (key, URL) of the style's sources, apart from GeoJSON `data`."""
    sources = style.get("sources")
    if not isinstance(sources, dict):
        return
    for source_id, source in sources.items():
        if not isinstance(source, dict):
            continue
        if isinstance(source.get("url"), str):
            yield f"sources.{source_id}.url", source["url"]
        for name in ("tiles", "urls"):
            if isinstance(source.get(name), list):
                for index, url in enumerate(source[name]):
                    if isinstance(url, str):
                        yield f"sources.{source_id}.{name}[{index}]", url


_HOST = re.compile(r"[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*")


def uses_basemap(style: dict[str, Any]) -> bool:
    """Whether a source of the style loads the local basemap, at the symbolic URL."""
    return any(url == BASEMAP_URL for _, url in _source_urls(style))


def _https_origin(url: str) -> str | None:
    """The origin of the `https` URL a source loads, also behind `pmtiles://`, or `None`.

    The origin goes into the Content-Security-Policy, so it is rebuilt from a host name
    (IDNA-encoded) and a port, and a URL with user info or any other host is refused.
    """
    parts = urlsplit(url.removeprefix("pmtiles://"))
    try:
        port = parts.port
        host = (parts.hostname or "").encode("idna").decode("ascii")
    except ValueError:  # Also a UnicodeError from the IDNA codec.
        return None
    if parts.scheme != "https" or "@" in parts.netloc or not _HOST.fullmatch(host):
        return None
    return f"https://{host}" if port is None else f"https://{host}:{port}"


def _check_sources(directory: Path, style: dict[str, Any], issues: _Issues) -> None:
    sources = style.get("sources")
    if not isinstance(sources, dict):
        issues.add("sources", "is required, as an object")
        return
    for source_id, source in sources.items():
        if isinstance(source, dict) and isinstance(source.get("data"), str):
            key = f"sources.{source_id}.data"
            file = _check_file(directory, source["data"], key, issues)
            if file is not None and file.stat().st_size > OVERLAY_MAX_BYTES:
                issues.add(
                    key,
                    f"{source['data']} is {file.stat().st_size / 1024 / 1024:.1f} MB; "
                    "an overlay may be at most 1 MB",
                )
    for key, url in _source_urls(style):
        if url != BASEMAP_URL and _https_origin(url) is None:
            issues.add(
                key, f"{url!r} must be {BASEMAP_URL} or an absolute https URL with a host name"
            )


def _layers(style: dict[str, Any]) -> list[dict[str, Any]]:
    layers = style.get("layers")
    if not isinstance(layers, list):
        return []
    return [layer for layer in layers if isinstance(layer, dict)]


def _check_layers(style: dict[str, Any], against: list[tuple[str, str]], issues: _Issues) -> None:
    """The banned properties and the contrast rules, layer by layer.

    `against` names the colours every fill needs 3:1 against: the theme's accent and
    `marker.ink`, as (name, `#RRGGBB`).
    """
    if not isinstance(style.get("layers"), list):
        issues.add("layers", "is required, as a list")
        return
    for index, layer in enumerate(style["layers"]):
        if not isinstance(layer, dict):
            continue
        paint = layer.get("paint") if isinstance(layer.get("paint"), dict) else {}
        layout = layer.get("layout") if isinstance(layer.get("layout"), dict) else {}
        where = f"layers[{index}]"
        named = f"layer {json.dumps(layer.get('id'))}"

        for group, properties in (("paint", paint), ("layout", layout)):
            for name in BANNED_PROPERTIES:
                if name in properties:
                    issues.add(
                        f"{where}.{group}.{name}",
                        f"is not allowed ({named}): dashes and patterns are reserved for "
                        "TART's signs; draw basemap lines continuous",
                    )

        for name in ("background-color", "fill-color"):
            if name not in paint:
                continue
            key = f"{where}.paint.{name}"
            for colour in _colours(paint[name], key, issues) or []:
                for target, target_colour in against:
                    ratio = contrast_ratio(colour, target_colour)
                    if ratio < FILL_MIN_CONTRAST:
                        issues.add(
                            key,
                            f"{colour} ({named}) has a contrast of {ratio:.2f}:1 against "
                            f"{target} {target_colour}; it needs at least "
                            f"{FILL_MIN_CONTRAST:g}:1",
                        )

        if layer.get("type") == "symbol" and "text-field" in layout:
            text_key, halo_key = f"{where}.paint.text-color", f"{where}.paint.text-halo-color"
            texts = _colours(paint.get("text-color", "#000000"), text_key, issues)
            if "text-halo-color" not in paint:
                issues.add(
                    halo_key,
                    f"is required ({named}): labels need a halo, at least "
                    f"{TEXT_MIN_CONTRAST:g}:1 against their text",
                )
                continue
            halos = _colours(paint["text-halo-color"], halo_key, issues, opaque=True)
            for text in texts or []:
                for halo in halos or []:
                    ratio = contrast_ratio(text, halo)
                    if ratio < TEXT_MIN_CONTRAST:
                        issues.add(
                            text_key,
                            f"{text} ({named}) has a contrast of {ratio:.2f}:1 against its "
                            f"text-halo-color {halo}; it needs at least {TEXT_MIN_CONTRAST:g}:1",
                        )


def _token(style: dict[str, Any], token: str) -> str | None:
    metadata = style.get("metadata")
    tokens = metadata.get(TOKENS) if isinstance(metadata, dict) else None
    value = tokens.get(token) if isinstance(tokens, dict) else None
    parsed = parse_colour(value) if isinstance(value, str) else None
    return parsed[0] if parsed else None


def _check_style(
    directory: Path, style: dict[str, Any], accent: str | None, issues: _Issues
) -> None:
    _check_metadata(style, issues)
    _check_fonts(directory, style, issues)
    _check_assets(directory, style, issues)
    _check_sources(directory, style, issues)
    against = [("the accent", accent), ("marker.ink", _token(style, "marker.ink"))]
    _check_layers(style, [(name, colour) for name, colour in against if colour], issues)


def _read(directory: Path, file: str, issues: _Issues) -> dict[str, Any] | None:
    path = directory / file
    if not path.is_file():
        issues.add("", "is missing")
        return None
    try:
        style = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        issues.add("", f"is not valid JSON: {error}")
        return None
    except RecursionError:
        issues.add("", "is nested too deeply")
        return None
    if not isinstance(style, dict):
        issues.add("", "must hold a style object")
        return None
    return style


def _ids(style: dict[str, Any], part: str) -> set[str]:
    if part == "sources":
        sources = style.get("sources")
        return set(sources) if isinstance(sources, dict) else set()
    return {layer["id"] for layer in _layers(style) if isinstance(layer.get("id"), str)}


def _check_parity(styles: Mapping[str, dict[str, Any]], issues: _Issues) -> None:
    """The dark style has the light style's source and layer ids, and no others."""
    light, dark = styles["light"], styles["dark"]
    for part, noun in (("sources", "source"), ("layers", "layer")):
        missing = sorted(_ids(light, part) - _ids(dark, part))
        extra = sorted(_ids(dark, part) - _ids(light, part))
        if missing:
            issues.add(part, f"lacks the {noun} ids {', '.join(missing)} of {STYLE_FILES['light']}")
        if extra:
            issues.add(
                part, f"has the {noun} ids {', '.join(extra)}, which {STYLE_FILES['light']} lacks"
            )


def _symbolic_links(directory: Path) -> list[tuple[str, str, str]]:
    """Every symbolic link under `map/`, as an issue.

    Caddy serves that directory as it is, and would follow a link out of it.
    """
    message = "must not be a symbolic link: Caddy serves map/ and would follow it"
    return [
        (path.relative_to(directory).as_posix(), "", message)
        for path in sorted((directory / "map").rglob("*"))
        if path.is_symlink()
    ]


def read_styles(
    directory: Path, accents: Mapping[str, str | None]
) -> tuple[dict[str, dict[str, Any]], list[tuple[str, str, str]]]:
    """Read and check both style files.

    `accents` holds the theme's accent from `instance.toml` as `#RRGGBB`, or `None`
    when it is itself invalid (its own issue is reported with `instance.toml`).
    Returns the styles by theme and the issues as (file, key, message).
    """
    styles: dict[str, dict[str, Any]] = {}
    found = _symbolic_links(directory)
    for theme, file in STYLE_FILES.items():
        issues = _Issues()
        style = _read(directory, file, issues)
        if style is not None:
            _check_style(directory, style, accents.get(theme), issues)
            styles[theme] = style
        found += [(file, key, message) for key, message in issues.items]
    if len(styles) == len(THEMES):
        issues = _Issues()
        _check_parity(styles, issues)
        found += [(STYLE_FILES["dark"], key, message) for key, message in issues.items]
    return styles, found


def external_origins(styles: Mapping[str, dict[str, Any]]) -> list[str]:
    """The origins of the styles' external `https` sources, for the Content-Security-Policy."""
    origins = set()
    for style in styles.values():
        for _, url in _source_urls(style):
            origin = _https_origin(url)
            if origin is not None:
                origins.add(origin)
    return sorted(origins)
