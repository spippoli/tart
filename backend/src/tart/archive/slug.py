"""The cosmetic slug of record URLs (ADR 0010, archive-records spec "Slug derivation")."""

import re
import unicodedata

MAX_SLUG_LENGTH = 60

# Latin letters that Unicode does not decompose into a base letter plus an accent;
# PostgreSQL's `unaccent`, which the spec names, folds them like this.
_FOLDED = str.maketrans(
    {
        "ß": "ss",
        "æ": "ae",
        "œ": "oe",
        "ø": "o",
        "ł": "l",
        "đ": "d",
        "ð": "d",
        "þ": "th",
        "\u0131": "i",
    }
)
_NOT_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    """Lowercase, strip accents, turn each non-alphanumeric run into `-`, trim, cut at 60.

    The cut falls on the last `-` that fits. An empty result means the record is
    canonical at its bare id.
    """
    folded = unicodedata.normalize("NFKD", name.lower().translate(_FOLDED))
    unaccented = "".join(char for char in folded if not unicodedata.combining(char))
    slug = _NOT_ALPHANUMERIC.sub("-", unaccented).strip("-")
    if len(slug) <= MAX_SLUG_LENGTH:
        return slug
    cut = slug[: MAX_SLUG_LENGTH + 1].rfind("-")
    return slug[:cut] if cut > 0 else slug[:MAX_SLUG_LENGTH]


def record_path_segment(record_id: int, name: str | None) -> str:
    """The canonical `{id}-{slug}` path segment, or the bare id without a usable name."""
    slug = slugify(name) if name else ""
    return f"{record_id}-{slug}" if slug else str(record_id)
