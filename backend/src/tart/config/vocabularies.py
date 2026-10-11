"""Open vocabularies (Foundations spec, 1. Instance configuration).

Each vocabulary file is an ordered list of entries; the list order is the display
order. An entry's `key` is what the database stores and never changes; entries are
retired, never deleted. Labels (and descriptions, when present) are UI strings, so
each enabled UI language needs one: the loader passes the enabled UI languages as
the validation context `ui_languages`.
"""

import re
from typing import Annotated

from pydantic import (
    AfterValidator,
    Field,
    StrictBool,
    StrictStr,
    ValidationInfo,
    field_validator,
)

from tart.config.instance import Table, Text
from tart.messages import UI_LANGUAGES, load_catalogue

VOCABULARIES = ("expression_types", "surface_types", "decision_reasons", "notice_reasons")
"""The open vocabularies, each read from `vocabularies/<name>.toml`."""

DUPLICATE = "duplicate"
"""The platform's Decision message reason, reserved in every vocabulary file."""

_KEY = re.compile(r"^[a-z][a-z0-9_]*$")


def _key(value: str) -> str:
    if not _KEY.match(value):
        raise ValueError(f"{value!r} is not a key (lowercase letters, digits, and _)")
    if value == DUPLICATE:
        raise ValueError(f"{DUPLICATE!r} is reserved for the platform's Decision message reason")
    return value


def _one_per_ui_language(texts: dict[str, str], info: ValidationInfo) -> dict[str, str]:
    unknown = sorted(set(texts) - set(UI_LANGUAGES))
    if unknown:
        raise ValueError(f"{', '.join(unknown)} is not a UI language of this TART release")
    enabled = (info.context or {}).get("ui_languages", ())
    missing = [language for language in enabled if language not in texts]
    if missing:
        raise ValueError(f"missing for the enabled UI language {', '.join(missing)}")
    return texts


Translations = Annotated[dict[str, Text], AfterValidator(_one_per_ui_language)]


class Entry(Table):
    key: Annotated[StrictStr, AfterValidator(_key)]
    label: Translations
    description: Translations | None = None
    retired: StrictBool = False


class VocabularyFile(Table):
    """One `vocabularies/<name>.toml`."""

    entries: Annotated[tuple[Entry, ...], Field(min_length=1)]

    @field_validator("entries")
    @classmethod
    def _usable(cls, entries: tuple[Entry, ...]) -> tuple[Entry, ...]:
        keys = [entry.key for entry in entries]
        duplicated = sorted({key for key in keys if keys.count(key) > 1})
        if duplicated:
            raise ValueError(f"the key {', '.join(duplicated)} appears more than once")
        if all(entry.retired for entry in entries):
            raise ValueError("every entry is retired; keep at least one that is not")
        return entries


def duplicate_entry() -> Entry:
    """The platform's `duplicate` reason, labelled from the backend message catalogue."""
    catalogue = load_catalogue()
    labels = {
        language: catalogue.render(language, "decision_reason_duplicate")
        for language in catalogue.languages
    }
    # Built without validation: its key is the one validation reserves.
    return Entry.model_construct(key=DUPLICATE, label=labels, description=None, retired=False)
