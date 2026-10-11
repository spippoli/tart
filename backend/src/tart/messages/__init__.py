"""The backend message catalogue: the email strings in every UI language (ADR 0008).

One flat JSON file per UI language, `{key: text}`, with `{name}` placeholders.
UI languages belong to the platform and ship complete, so a key present in one
language and missing from another is an error: loading fails, and the test
suite fails CI.
"""

import json
from dataclasses import dataclass
from pathlib import Path

UI_LANGUAGES = ("it", "en")
"""The platform's UI languages; an Instance enables a subset."""

_CATALOGUE_DIR = Path(__file__).parent


class MissingMessageKeysError(Exception):
    def __init__(self, missing: list[tuple[str, str]]) -> None:
        self.missing = missing
        lines = "\n".join(f"  {language}: {key}" for language, key in missing)
        super().__init__(f"Missing message keys:\n{lines}")


def _read(directory: Path, language: str) -> dict[str, str]:
    path = directory / f"{language}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def find_missing_keys(
    directory: Path = _CATALOGUE_DIR, languages: tuple[str, ...] = UI_LANGUAGES
) -> list[tuple[str, str]]:
    """Lists `(language, key)` for each key that another language has and this one lacks."""
    keys = {language: set(_read(directory, language)) for language in languages}
    all_keys = sorted(set().union(*keys.values()))
    return [
        (language, key) for language in languages for key in all_keys if key not in keys[language]
    ]


@dataclass(frozen=True)
class Catalogue:
    messages: dict[str, dict[str, str]]

    @property
    def languages(self) -> tuple[str, ...]:
        return tuple(self.messages)

    def render(self, language: str, key: str, **params: object) -> str:
        return self.messages[language][key].format_map(params)


def load_catalogue(
    directory: Path = _CATALOGUE_DIR, languages: tuple[str, ...] = UI_LANGUAGES
) -> Catalogue:
    missing = find_missing_keys(directory, languages)
    if missing:
        raise MissingMessageKeysError(missing)
    return Catalogue({language: _read(directory, language) for language in languages})
