import json
from pathlib import Path

from tart.api.app import create_app
from tart.api.openapi import openapi_document

# The frontend generates its API client from this committed copy of the schema.
COMMITTED_SCHEMA = Path(__file__).parents[2] / "frontend" / "src" / "lib" / "api" / "openapi.json"


def test_the_document_is_the_app_schema() -> None:
    assert json.loads(openapi_document()) == create_app().openapi()


def test_the_committed_schema_matches_the_api() -> None:
    assert COMMITTED_SCHEMA.read_text(encoding="utf-8") == openapi_document(), (
        "The OpenAPI schema drifted. Run in backend/: "
        "uv run python -m tart.api.openapi > ../frontend/src/lib/api/openapi.json, "
        "then pnpm api:generate in frontend/."
    )
