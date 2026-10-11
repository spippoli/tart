"""Prints the API's OpenAPI schema, from which the frontend generates its client (ADR 0004).

uv run python -m tart.api.openapi > ../frontend/src/lib/api/openapi.json

The printed copy describes the API contract, not a build: its `info.version` is always
the repository's own 0.0.0, so the committed copy does not drift when a release writes
its version into pyproject.toml (ADR 0021). The served `/api/openapi.json` carries the
installed version.
"""

import json

from tart.api.app import create_app

UNVERSIONED = "0.0.0"


def openapi_document() -> str:
    schema = create_app().openapi()
    schema["info"]["version"] = UNVERSIONED
    return json.dumps(schema, indent=2, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    print(openapi_document(), end="")
