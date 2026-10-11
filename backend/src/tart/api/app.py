from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from tart.migrations import ensure_database_at_head


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Refuse to start on a database the code does not match; never migrate here (ADR 0020).
    await ensure_database_at_head()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="TART API",
        # The release writes its version into pyproject.toml (ADR 0021); 0.0.0 from source.
        version=version("tart"),
        openapi_url="/api/openapi.json",
        docs_url=None,
        redoc_url=None,
        lifespan=_lifespan,
    )

    @app.get("/api/health", response_class=PlainTextResponse)
    def health() -> str:
        # Liveness only; the Health module (Operations spec) adds the checks.
        return "ok"

    return app
