import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import PlainTextResponse

from tart import jobs, tiles
from tart.api import auth, csrf, map_style
from tart.config import config_dir
from tart.config.public import PublicConfiguration, public_configuration
from tart.db import create_engine
from tart.messages import load_catalogue
from tart.startup import start

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Load the configuration once, and refuse to start on an invalid one or on a database
    # the code does not match; never migrate here (ADR 0020). There is no hot reload.
    configuration = await start()
    app.state.configuration = configuration
    app.state.public_configuration = public_configuration(configuration.instance)
    # A missing or stale basemap only hides the map: warn, never stop.
    for warning in tiles.startup_warnings(
        config_dir(os.environ), configuration.environment.PMTILES_PATH
    ):
        logger.warning("basemap: %s", warning)
    app.state.catalogue = load_catalogue()
    database_url = configuration.environment.DATABASE_URL.get_secret_value()
    app.state.engine = create_engine(database_url)
    # The api only defers jobs, such as emails; the `worker` runs them.
    app.state.jobs = jobs.create_app(jobs.connector_for(database_url))
    try:
        async with app.state.jobs.open_async():
            yield
    finally:
        await app.state.engine.dispose()


def get_public_configuration(request: Request) -> PublicConfiguration:
    """The public subset of the configuration loaded at startup."""
    return request.app.state.public_configuration


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

    @app.get("/api/config")
    def config(
        public: Annotated[PublicConfiguration, Depends(get_public_configuration)],
    ) -> PublicConfiguration:
        """The public subset of the Instance configuration, which the frontend caches."""
        return public

    app.middleware("http")(csrf.check)
    app.include_router(auth.router)
    app.include_router(map_style.router)
    return app
