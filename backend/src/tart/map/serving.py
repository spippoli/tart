"""A style as the browser gets it (Discovery spec, Map style ownership and serving).

    served_style(style, base_url, accent, tiles_dir) -> ServedStyle   # or TilesMissing

Root-relative asset paths become absolute URLs from the public base URL, the
symbolic basemap URL becomes the current extract named by the tile manifest, and
the platform adds the theme's accent to the archive-layer tokens, which the map
module reads with the insertion point from the style's metadata. The ETag hashes
the served document, so it changes with the configuration (on a restart) and with
the extract (after `tart tiles update`).
"""

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tart.map.style import ACCENT_TOKEN, ASSET_PREFIX, BASEMAP_URL, TOKENS

MANIFEST = "manifest.json"
"""The tile manifest in the PMTiles directory, written by `tart tiles update`."""
MANIFEST_FILE_KEY = "file"
"""The manifest key naming the current extract, a file in the same directory."""
TILES_PREFIX = "/tiles/"
"""Where Caddy serves the PMTiles directory."""

_EXTRACT = re.compile(r"^basemap-\d{8}\.pmtiles$")


class TilesMissing(Exception):
    """The style uses the local basemap, and there is no current extract."""


@dataclass(frozen=True)
class ServedStyle:
    body: bytes
    etag: str
    """A strong ETag, quoted."""


def current_extract(tiles_dir: Path) -> str | None:
    """The file name of the current basemap extract, or `None` if there is none."""
    try:
        manifest = json.loads((tiles_dir / MANIFEST).read_text(encoding="utf-8"))
    except OSError, ValueError:
        return None
    name = manifest.get(MANIFEST_FILE_KEY) if isinstance(manifest, dict) else None
    if not isinstance(name, str) or not _EXTRACT.match(name):
        return None
    return name if (tiles_dir / name).is_file() else None


def _absolute(value: Any, base_url: str) -> Any:
    if isinstance(value, str) and value.startswith(ASSET_PREFIX):
        return base_url + value
    return value


def _rewrite_sources(style: dict[str, Any], base_url: str, tiles_dir: Path) -> None:
    extract: str | None = None
    for source in style.get("sources", {}).values():
        if "data" in source:
            source["data"] = _absolute(source["data"], base_url)
        urls = [("url", source)] if "url" in source else []
        urls += [(index, source["tiles"]) for index in range(len(source.get("tiles", [])))]
        for key, holder in urls:
            if holder[key] == BASEMAP_URL:
                extract = extract or current_extract(tiles_dir)
                if extract is None:
                    raise TilesMissing
                holder[key] = f"pmtiles://{base_url}{TILES_PREFIX}{extract}"


def served_style(style: dict[str, Any], base_url: str, accent: str, tiles_dir: Path) -> ServedStyle:
    """The style rewritten for the browser, or `TilesMissing`.

    `style` is a validated style file; `base_url` is the public base URL.
    """
    base_url = base_url.rstrip("/")
    served = copy.deepcopy(style)

    if isinstance(served.get("glyphs"), str):
        served["glyphs"] = _absolute(served["glyphs"], base_url)
    sprite = served.get("sprite")
    if isinstance(sprite, str):
        served["sprite"] = _absolute(sprite, base_url)
    elif isinstance(sprite, list):
        for entry in sprite:
            entry["url"] = _absolute(entry["url"], base_url)
    for font, face in served.get("font-faces", {}).items():
        if isinstance(face, list):
            for entry in face:
                entry["url"] = _absolute(entry["url"], base_url)
        else:
            served["font-faces"][font] = _absolute(face, base_url)
    _rewrite_sources(served, base_url, tiles_dir)
    served["metadata"][TOKENS][ACCENT_TOKEN] = accent

    body = json.dumps(served, ensure_ascii=False, separators=(",", ":")).encode()
    return ServedStyle(body, f'"{hashlib.sha256(body).hexdigest()}"')
