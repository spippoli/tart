import asyncio
import time
import uuid
from collections.abc import Iterator

import asyncpg
import pytest
from testcontainers.core.container import DockerContainer

# Same image as the `db` service in deploy/compose.yaml; keep the two in step.
POSTGIS_IMAGE = (
    "postgis/postgis:18-3.6@sha256:60f6ad1d21ea86a67d47780b9a0d1e1d200500f62b19293fa834d0dea80b8677"
)
PASSWORD = "test"


def execute(dsn: str, statement: str) -> None:
    """Run one statement through a plain asyncpg connection (`postgresql://` DSN)."""

    async def run() -> None:
        connection = await asyncpg.connect(dsn)
        try:
            await connection.execute(statement)
        finally:
            await connection.close()

    asyncio.run(run())


def fetch_value(dsn: str, query: str) -> object:
    async def run() -> object:
        connection = await asyncpg.connect(dsn)
        try:
            return await connection.fetchval(query)
        finally:
            await connection.close()

    return asyncio.run(run())


def _wait_until_ready(dsn: str, timeout: float = 60) -> None:
    # The image's init phase listens on a Unix socket only, so the first TCP
    # connection that succeeds reaches the final server.
    deadline = time.monotonic() + timeout
    while True:
        try:
            execute(dsn, "SELECT 1")
            return
        except OSError, asyncpg.PostgresError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.5)


@pytest.fixture(scope="session")
def postgres_server() -> Iterator[str]:
    """A PostGIS server for the whole session, as `user:password@host:port`."""
    container = (
        DockerContainer(POSTGIS_IMAGE)
        .with_env("POSTGRES_PASSWORD", PASSWORD)
        .with_exposed_ports(5432)
    )
    with container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(5432)
        server = f"postgres:{PASSWORD}@{host}:{port}"
        _wait_until_ready(f"postgresql://{server}/postgres")
        yield server


@pytest.fixture
def database(postgres_server: str, monkeypatch: pytest.MonkeyPatch) -> str:
    """A new, empty database for one test, exported as DATABASE_URL.

    Returns its plain `postgresql://` DSN for direct inspection.
    """
    name = f"test_{uuid.uuid4().hex}"
    execute(f"postgresql://{postgres_server}/postgres", f'CREATE DATABASE "{name}"')
    monkeypatch.setenv("DATABASE_URL", f"postgresql+asyncpg://{postgres_server}/{name}")
    return f"postgresql://{postgres_server}/{name}"
