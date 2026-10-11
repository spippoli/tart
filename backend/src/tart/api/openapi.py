"""Prints the API's OpenAPI schema, from which the frontend generates its client (ADR 0004).

    uv run python -m tart.api.openapi > ../frontend/src/lib/api/openapi.json
"""

import json

from tart.api.app import create_app


def openapi_document() -> str:
    return json.dumps(create_app().openapi(), indent=2, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    print(openapi_document(), end="")
