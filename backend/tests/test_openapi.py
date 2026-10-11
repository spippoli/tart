import json
from importlib.metadata import version
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tart.api import app as app_module
from tart.api.app import create_app
from tart.api.openapi import UNVERSIONED, openapi_document

# The frontend generates its API client from this committed copy of the schema.
COMMITTED_SCHEMA = Path(__file__).parents[2] / "frontend" / "src" / "lib" / "api" / "openapi.json"


def _released_as(monkeypatch: pytest.MonkeyPatch, release: str) -> None:
    """Make the installed package report `release`, as in a release build (ADR 0021)."""
    monkeypatch.setattr(app_module, "version", lambda _: release)


def test_the_document_is_the_app_schema_without_its_version() -> None:
    document = json.loads(openapi_document())
    schema = create_app().openapi()

    assert document["info"].pop("version") == UNVERSIONED
    del schema["info"]["version"]
    assert document == schema


def test_the_committed_schema_matches_the_api() -> None:
    assert COMMITTED_SCHEMA.read_text(encoding="utf-8") == openapi_document(), (
        "The OpenAPI schema drifted. Run in backend/: "
        "uv run python -m tart.api.openapi > ../frontend/src/lib/api/openapi.json, "
        "then pnpm api:generate in frontend/."
    )


def test_the_api_reports_the_installed_version() -> None:
    response = TestClient(create_app()).get("/api/openapi.json")

    assert response.json()["info"]["version"] == version("tart")


def test_the_api_reports_a_release_version(monkeypatch: pytest.MonkeyPatch) -> None:
    _released_as(monkeypatch, "0.3.0")

    response = TestClient(create_app()).get("/api/openapi.json")

    assert response.json()["info"]["version"] == "0.3.0"


def test_a_release_version_does_not_drift_the_committed_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _released_as(monkeypatch, "0.3.0")

    assert COMMITTED_SCHEMA.read_text(encoding="utf-8") == openapi_document()
