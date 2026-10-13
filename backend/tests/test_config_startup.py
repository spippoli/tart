"""Foundations spec, 1. Instance configuration: startup, the database checks, and the
public configuration endpoint.

The database checks run against a test table registered as a vocabulary column and
as the terms acceptance column, as the tables of later tickets will be.
"""

import subprocess
import sys
from pathlib import Path

import pytest
from conftest import ENVIRONMENT, VALID_CONFIG, config_fixture, execute
from fastapi.testclient import TestClient

from tart.api.app import create_app, get_public_configuration
from tart.cli import main as run_cli
from tart.config import ConfigurationError, load_instance
from tart.config import database as database_checks
from tart.config.database import Column
from tart.config.public import public_configuration

SECRETS = {
    "SESSION_KEY": "a-session-key-that-must-never-be-public-0123",
    "SMTP_PASSWORD": "an-smtp-password-that-must-never-be-public",
    "SMTP_USERNAME": "smtp-user-never-public",
}


@pytest.fixture
def migrated(database: str) -> str:
    run_cli(["migrate"])
    return database


@pytest.fixture
def used_in_database(migrated: str, monkeypatch: pytest.MonkeyPatch) -> str:
    """A test table that stores the retired Expression type `sticker` and accepted terms v2."""
    execute(migrated, "CREATE TABLE test_records (expression_types text[], terms_version int)")
    execute(migrated, "INSERT INTO test_records VALUES (ARRAY['mural', 'sticker'], 1)")
    monkeypatch.setattr(
        database_checks,
        "VOCABULARY_COLUMNS",
        {"expression_types": (Column("test_records", "expression_types"),)},
    )
    monkeypatch.setattr(
        database_checks, "TERMS_ACCEPTANCE_COLUMN", Column("test_records", "terms_version")
    )
    return migrated


def _client_for(directory: Path) -> TestClient:
    app = create_app()
    instance = load_instance(directory)
    app.dependency_overrides[get_public_configuration] = lambda: public_configuration(instance)
    return TestClient(app)


def _start(
    module: list[str], monkeypatch: pytest.MonkeyPatch, directory: Path
) -> subprocess.CompletedProcess[str]:
    monkeypatch.setenv("CONFIG_DIR", str(directory))
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://tart:x@127.0.0.1:9/tart")
    return subprocess.run(
        [sys.executable, "-m", *module], capture_output=True, text=True, timeout=20
    )


def test_criterion_1_the_api_starts_with_a_valid_configuration(migrated: str) -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/config")

    assert response.status_code == 200
    assert response.json()["identity"]["name"] == "Archivio di prova dell'arte urbana"


@pytest.mark.parametrize(
    "module",
    [
        ["uvicorn", "tart.api.app:create_app", "--factory", "--port", "0"],
        ["tart.worker"],
    ],
    ids=["api", "worker"],
)
def test_criterion_2_startup_stops_and_lists_every_error(
    module: list[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _start(module, monkeypatch, config_fixture("several_errors", tmp_path))

    assert result.returncode != 0
    assert "invalid configuration, 3 error(s)" in result.stderr
    assert "instance.toml: config_version: is 2" in result.stderr
    assert "instance.toml: map.attribution: must not be empty" in result.stderr
    assert "texts/privacy.md: is missing" in result.stderr


def test_criterion_6_a_retired_key_in_use_starts_and_still_displays(
    used_in_database: str,
) -> None:
    with TestClient(create_app()) as client:
        expression_types = client.get("/api/config").json()["vocabularies"]["expression_types"]

    sticker = next(entry for entry in expression_types if entry["key"] == "sticker")
    assert sticker["retired"] is True
    assert sticker["label"] == {"it": "Sticker", "en": "Sticker"}


def test_criteria_6_and_43_removing_a_key_in_use_fails_startup(
    used_in_database: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONFIG_DIR", str(config_fixture("vocabulary_key_removed", tmp_path)))

    with pytest.raises(ConfigurationError) as raised, TestClient(create_app()):
        pass

    (issue,) = raised.value.issues
    assert (issue.file, issue.key) == ("vocabularies/expression_types.toml", "entries")
    assert "'sticker'" in issue.message


def test_criterion_43_config_check_database_fails_on_a_key_in_use_but_absent(
    used_in_database: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("CONFIG_DIR", str(config_fixture("vocabulary_key_removed", tmp_path)))

    assert run_cli(["config", "check"]) == 0
    assert run_cli(["config", "check", "--database"]) == 1
    assert "vocabularies/expression_types.toml: entries: the key 'sticker'" in (
        capsys.readouterr().err
    )


def test_criterion_43_a_terms_version_below_the_accepted_one_fails(
    used_in_database: str, capsys: pytest.CaptureFixture[str]
) -> None:
    execute(used_in_database, "INSERT INTO test_records VALUES (NULL, 2)")

    assert run_cli(["config", "check", "--database"]) == 1
    assert "instance.toml: terms.version: is 1, lower than version 2" in capsys.readouterr().err
    with pytest.raises(ConfigurationError, match=r"terms\.version"), TestClient(create_app()):
        pass


def test_criterion_43_config_check_database_succeeds_on_a_consistent_database(
    used_in_database: str,
) -> None:
    assert run_cli(["config", "check", "--database"]) == 0


def test_criterion_8_the_endpoint_exposes_no_environment_value(
    migrated: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name, value in SECRETS.items():
        monkeypatch.setenv(name, value)

    with TestClient(create_app()) as client:
        body = client.get("/api/config").text

    database_url = f"postgresql+asyncpg://{migrated.removeprefix('postgresql://')}"
    exposed = [
        *SECRETS.values(),
        database_url,
        ENVIRONMENT["PUBLIC_BASE_URL"],
        ENVIRONMENT["SMTP_HOST"],
        str(VALID_CONFIG),
    ]
    assert [value for value in exposed if value in body] == []


def test_criterion_9_a_changed_file_has_no_effect_until_a_restart(
    migrated: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = config_fixture("no_general_contact", tmp_path)
    monkeypatch.setenv("CONFIG_DIR", str(directory))
    instance_file = directory / "instance.toml"

    with TestClient(create_app()) as client:
        instance_file.write_text(
            instance_file.read_text(encoding="utf-8").replace(
                'name = "Archivio di prova', 'name = "Archivio cambiato'
            ),
            encoding="utf-8",
        )
        assert client.get("/api/config").json()["identity"]["name"].startswith("Archivio di")

    with TestClient(create_app()) as restarted:
        assert restarted.get("/api/config").json()["identity"]["name"].startswith("Archivio camb")


def test_criterion_41_the_endpoint_keeps_the_order_of_languages_and_licences() -> None:
    body = _client_for(VALID_CONFIG).get("/api/config").json()

    assert body["languages"]["ui"] == ["it", "en"]
    assert body["licenses"]["files"] == ["CC-BY-SA-4.0", "CC-BY-4.0", "CC0-1.0"]


def test_criterion_42_the_endpoint_lists_decision_reasons_then_duplicate() -> None:
    body = _client_for(VALID_CONFIG).get("/api/config").json()

    reasons = body["vocabularies"]["decision_reasons"]
    assert [reason["key"] for reason in reasons] == ["evidence", "location", "other", "duplicate"]
    assert reasons[-1]["label"]["it"] == "Duplicato di un record esistente"
    assert reasons[-1]["label"]["en"] == "Duplicate of an existing record"


def test_the_endpoint_carries_the_public_subset() -> None:
    body = _client_for(VALID_CONFIG).get("/api/config").json()

    assert set(body) == {
        "identity",
        "operator_name",
        "contacts",
        "languages",
        "geography",
        "map_attribution",
        "map_tile_origins",
        "vocabularies",
        "registration",
        "min_age",
        "licenses",
        "terms_version",
        "texts",
    }
    assert body["identity"]["logo"]["light"].startswith("<svg")
    assert body["identity"]["accent"] == {"light": "#7A2E1C", "dark": "#F0A08C"}
    assert body["contacts"]["dsa"] == "dsa@example.org"
    assert (body["registration"], body["min_age"]) == ("open", 14)
    assert body["geography"]["bounds"] == [12.40, 41.85, 12.56, 41.95]
    assert body["texts"]["privacy"].startswith("# privacy")
