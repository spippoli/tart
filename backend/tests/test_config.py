"""Foundations spec, 1. Instance configuration: the loader and `tart config check`.

A directory and an environment in, a validated configuration or a complete error
list out. One fixture directory per failure, under `fixtures/config/failures`, laid
over the valid configuration; each runs through the loader and `tart config check`.
"""

from pathlib import Path

import pytest
from conftest import ENVIRONMENT, VALID_CONFIG, config_fixture

from tart.cli import main as run_cli
from tart.config import ConfigurationError, load_configuration, load_environment, load_instance
from tart.config.instance import InstanceFile
from tart.config.vocabularies import VocabularyFile

ENVIRONMENT_WITH_DATABASE = {
    **ENVIRONMENT,
    "DATABASE_URL": "postgresql+asyncpg://tart:secret-db-password@db:5432/tart",
}

# Fixture name -> the (file, key) of every issue it must produce, and nothing else.
FAILURES = {
    # Criterion 3.
    "unknown_key": [("instance.toml", "operator.website")],
    "wrong_config_version": [("instance.toml", "config_version")],
    "missing_label": [("vocabularies/expression_types.toml", "entries[0].label")],
    "ui_language_not_in_image": [("instance.toml", "languages.ui[2]")],
    "empty_attribution": [("instance.toml", "map.attribution")],
    "missing_terms": [("texts/terms.md", "")],
    "missing_privacy_policy": [("texts/privacy.md", "")],
    "missing_dsa_contact": [("instance.toml", "contacts.dsa")],
    # Criterion 4 (the UI backgrounds; the map fills are checked with the map style).
    "low_contrast_accent_light": [("instance.toml", "identity.accent.light")],
    "low_contrast_accent_dark": [("instance.toml", "identity.accent.dark")],
    # Criterion 40.
    "moved_logo": [("instance.toml", "identity.logo.light"), ("identity/logo.light.svg", "")],
    # Criterion 42.
    "all_retired": [("vocabularies/surface_types.toml", "entries")],
    "reserved_duplicate_key": [("vocabularies/decision_reasons.toml", "entries[1].key")],
    # Criterion 44.
    "missing_dsa_languages": [("instance.toml", "contacts.dsa_languages")],
    "missing_privacy_contact": [("instance.toml", "contacts.privacy")],
    "missing_operator_name": [("instance.toml", "operator.name")],
    # The licence rules of 1. Instance configuration.
    "empty_file_licences": [("instance.toml", "licenses.files")],
    "duplicated_file_licence": [("instance.toml", "licenses.files")],
    "licence_outside_platform_list": [("instance.toml", "licenses.data")],
}

SEVERAL_ERRORS = [
    ("instance.toml", "config_version"),
    ("instance.toml", "map.attribution"),
    ("texts/privacy.md", ""),
]


def _issues(directory: Path) -> list[tuple[str, str]]:
    with pytest.raises(ConfigurationError) as raised:
        load_instance(directory)
    return [(issue.file, issue.key) for issue in raised.value.issues]


def _check(directory: Path, monkeypatch: pytest.MonkeyPatch, *args: str) -> int:
    monkeypatch.setenv("CONFIG_DIR", str(directory))
    return run_cli(["config", "check", *args])


def test_criteria_1_and_40_the_valid_configuration_loads_with_every_table() -> None:
    configuration = load_configuration(VALID_CONFIG, ENVIRONMENT_WITH_DATABASE)

    settings = configuration.instance.settings
    assert settings.identity.name == "Archivio di prova dell'arte urbana"
    assert settings.operator.name == "Associazione di prova (fittizia)"
    assert settings.contacts.dsa_languages == ("it", "en")
    assert settings.geography.default_view.center == (12.4823, 41.8955)
    assert settings.map.attribution[0].text == "© OpenStreetMap"
    assert settings.community.registration == "open"
    assert settings.media.public_rendition_max_px == 2048
    assert settings.terms.version == 1
    assert configuration.instance.texts["terms"].startswith("# terms")
    assert configuration.instance.bounds == (12.40, 41.85, 12.56, 41.95)


def test_criterion_1_config_check_succeeds_on_the_valid_configuration(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _check(VALID_CONFIG, monkeypatch) == 0
    assert "the configuration is valid" in capsys.readouterr().out


@pytest.mark.parametrize("name", FAILURES)
def test_criteria_3_4_40_42_44_each_failure_fails_validation(name: str, tmp_path: Path) -> None:
    assert _issues(config_fixture(name, tmp_path)) == FAILURES[name]


@pytest.mark.parametrize("name", FAILURES)
def test_criteria_3_4_40_42_44_config_check_fails_on_each_failure(
    name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = _check(config_fixture(name, tmp_path), monkeypatch)

    assert status == 1
    errors = capsys.readouterr().err
    for file, key in FAILURES[name]:
        assert (f"{file}: {key}:" if key else f"{file}:") in errors


def test_criterion_2_several_errors_are_all_listed(tmp_path: Path) -> None:
    assert _issues(config_fixture("several_errors", tmp_path)) == SEVERAL_ERRORS


def test_criterion_2_config_check_prints_the_same_list_and_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    directory = config_fixture("several_errors", tmp_path)
    with pytest.raises(ConfigurationError) as raised:
        load_instance(directory)

    status = _check(directory, monkeypatch)

    assert status == 1
    assert capsys.readouterr().err.strip() == str(raised.value).strip()


def test_criterion_3_messages_name_the_problem(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError) as raised:
        load_instance(config_fixture("several_errors", tmp_path))

    lines = str(raised.value).splitlines()
    assert lines[0] == "invalid configuration, 3 error(s):"
    assert "release notes" in lines[1]
    assert lines[3] == "  texts/privacy.md: is missing"


def test_criterion_4_the_accent_needs_3_to_1_against_its_theme_background(
    tmp_path: Path,
) -> None:
    with pytest.raises(ConfigurationError) as raised:
        load_instance(config_fixture("low_contrast_accent_dark", tmp_path))

    (issue,) = raised.value.issues
    assert "#121212" in issue.message
    assert "3:1" in issue.message


def test_criterion_41_the_first_ui_language_and_file_licence_are_the_defaults() -> None:
    settings = load_instance(VALID_CONFIG).settings

    assert settings.languages.default_ui == "it"
    assert settings.licenses.default_file == "CC-BY-SA-4.0"
    assert settings.licenses.files == ("CC-BY-SA-4.0", "CC-BY-4.0", "CC0-1.0")


def test_criterion_44_the_general_contact_may_be_absent(tmp_path: Path) -> None:
    instance = load_instance(config_fixture("no_general_contact", tmp_path))

    assert instance.settings.contacts.general is None


def test_criterion_42_decision_reasons_end_with_the_platform_duplicate() -> None:
    reasons = load_instance(VALID_CONFIG).vocabularies["decision_reasons"]

    assert [reason.key for reason in reasons] == ["evidence", "location", "other", "duplicate"]
    assert reasons[-1].label == {
        "it": "Duplicato di un record esistente",
        "en": "Duplicate of an existing record",
    }
    assert not reasons[-1].retired


def test_criterion_7_secrets_and_connections_come_from_the_environment() -> None:
    configuration = load_configuration(VALID_CONFIG, ENVIRONMENT_WITH_DATABASE)

    environment = configuration.environment
    assert environment.SESSION_KEY.get_secret_value() == ENVIRONMENT["SESSION_KEY"]
    assert environment.DATABASE_URL.get_secret_value() == ENVIRONMENT_WITH_DATABASE["DATABASE_URL"]
    assert str(environment.PUBLIC_BASE_URL) == "https://archive.example.org/"
    assert environment.SMTP_HOST == "smtp.example.org"
    assert environment.STORAGE_BACKEND == "filesystem"


def test_criterion_7_the_configuration_directory_holds_no_secret(tmp_path: Path) -> None:
    directory = config_fixture("unknown_key", tmp_path)
    toml = directory / "instance.toml"
    toml.write_text(
        toml.read_text(encoding="utf-8").replace(
            'website = "https://example.org"', 'session_key = "a-secret-in-the-wrong-place"'
        ),
        encoding="utf-8",
    )

    assert _issues(directory) == [("instance.toml", "operator.session_key")]


def _keys(schema: object) -> set[str]:
    if isinstance(schema, dict):
        return {
            *schema.get("properties", {}),
            *(key for value in schema.values() for key in _keys(value)),
        }
    if isinstance(schema, list):
        return {key for value in schema for key in _keys(value)}
    return set()


def test_criterion_7_no_configuration_file_has_a_key_for_a_secret_or_a_connection() -> None:
    keys = _keys(InstanceFile.model_json_schema()) | _keys(VocabularyFile.model_json_schema())

    forbidden = ("password", "secret", "session", "database", "smtp", "s3", "credential")
    assert not [key for key in keys if any(word in key.lower() for word in forbidden)]


def test_criterion_7_a_missing_secret_or_connection_setting_is_an_error() -> None:
    with pytest.raises(ConfigurationError) as raised:
        load_environment({"STORAGE_BACKEND": "s3"})

    assert [(issue.file, issue.key) for issue in raised.value.issues] == [
        ("environment", "DATABASE_URL"),
        ("environment", "PUBLIC_BASE_URL"),
        ("environment", "SESSION_KEY"),
        ("environment", "SMTP_HOST"),
        ("environment", "SMTP_FROM"),
    ]


def test_criterion_7_s3_storage_needs_its_endpoint_bucket_and_credentials() -> None:
    with pytest.raises(ConfigurationError) as raised:
        load_environment({**ENVIRONMENT_WITH_DATABASE, "STORAGE_BACKEND": "s3"})

    (issue,) = raised.value.issues
    assert issue.message == (
        "STORAGE_BACKEND=s3 also needs S3_ENDPOINT_URL, S3_REGION, S3_BUCKET, "
        "S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY"
    )


def test_errors_of_the_directory_and_the_environment_are_reported_together(
    tmp_path: Path,
) -> None:
    with pytest.raises(ConfigurationError) as raised:
        load_configuration(config_fixture("missing_terms", tmp_path), {})

    keys = [(issue.file, issue.key) for issue in raised.value.issues]
    assert keys[0] == ("texts/terms.md", "")
    assert ("environment", "SESSION_KEY") in keys


def test_criterion_43_config_check_needs_no_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Nothing listens there, and without --database nothing tries.
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://tart:x@127.0.0.1:9/tart")

    assert _check(VALID_CONFIG, monkeypatch) == 0


def test_criterion_43_config_check_with_database_fails_when_it_is_unreachable(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://tart:x@127.0.0.1:9/tart")

    assert _check(VALID_CONFIG, monkeypatch, "--database") == 1
    assert "cannot check the database" in capsys.readouterr().err


@pytest.mark.parametrize("file", ["instance", "vocabulary"])
def test_config_schema_prints_a_json_schema_for_editors(
    file: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run_cli(["config", "schema", file]) == 0

    assert '"additionalProperties": false' in capsys.readouterr().out
