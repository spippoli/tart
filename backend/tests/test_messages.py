import json
from pathlib import Path

import pytest

from tart.messages import (
    UI_LANGUAGES,
    MissingMessageKeysError,
    find_missing_keys,
    load_catalogue,
)


def _write_catalogues(directory: Path, catalogues: dict[str, dict[str, str]]) -> Path:
    for language, messages in catalogues.items():
        (directory / f"{language}.json").write_text(json.dumps(messages), encoding="utf-8")
    return directory


def test_the_shipped_catalogue_has_every_key_in_every_ui_language() -> None:
    catalogue = load_catalogue()

    assert catalogue.languages == UI_LANGUAGES


def test_a_key_missing_from_any_language_is_reported(tmp_path: Path) -> None:
    directory = _write_catalogues(
        tmp_path,
        {"it": {"greeting": "Ciao", "only_it": "Solo"}, "en": {"greeting": "Hello"}},
    )

    assert find_missing_keys(directory, ("it", "en")) == [("en", "only_it")]


def test_a_missing_catalogue_file_reports_all_its_keys(tmp_path: Path) -> None:
    directory = _write_catalogues(tmp_path, {"it": {"greeting": "Ciao"}})

    assert find_missing_keys(directory, ("it", "en")) == [("en", "greeting")]


def test_loading_an_incomplete_catalogue_fails(tmp_path: Path) -> None:
    directory = _write_catalogues(tmp_path, {"it": {"greeting": "Ciao"}, "en": {}})

    with pytest.raises(MissingMessageKeysError, match="en: greeting"):
        load_catalogue(directory, ("it", "en"))


def test_a_message_is_rendered_in_the_requested_language_with_its_parameters(
    tmp_path: Path,
) -> None:
    directory = _write_catalogues(
        tmp_path, {"it": {"hello": "Ciao, {name}"}, "en": {"hello": "Hello, {name}"}}
    )
    catalogue = load_catalogue(directory, ("it", "en"))

    assert catalogue.render("en", "hello", name="Roma") == "Hello, Roma"
    assert catalogue.render("it", "hello", name="Roma") == "Ciao, Roma"


def test_the_email_subject_names_the_archive_then_the_event() -> None:
    catalogue = load_catalogue()

    subject = catalogue.render(
        "it", "email_subject", archive_name="Archivio dell'arte urbana di Roma", event="Codice"
    )

    assert subject == "[Archivio dell'arte urbana di Roma] Codice"
