import asyncio
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Iterator

import aiobotocore.session
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


# An S3-compatible server for the S3 storage adapter's tests: the Versity S3
# Gateway (Apache-2.0) over a directory in the container.
S3_IMAGE = (
    "versity/versitygw:v1.8.0"
    "@sha256:30292fc2eeacc67a36993b01f7a7a5e3361a19cced0e80c1d71cfa2a4b0a2499"
)
S3_ACCESS_KEY = "tart-test"
S3_SECRET_KEY = "tart-test-secret"
S3_REGION = "us-east-1"


@pytest.fixture(scope="session")
def s3_server() -> Iterator[str]:
    """The endpoint URL of an S3-compatible server for the whole session."""
    container = (
        DockerContainer(S3_IMAGE)
        .with_kwargs(entrypoint="sh")
        .with_command(
            [
                "-c",
                f"mkdir -p /tmp/s3 && exec versitygw --access {S3_ACCESS_KEY} "
                f"--secret {S3_SECRET_KEY} --region {S3_REGION} posix /tmp/s3",
            ]
        )
        .with_exposed_ports(7070)
    )
    with container:
        endpoint_url = (
            f"http://{container.get_container_host_ip()}:{container.get_exposed_port(7070)}"
        )
        _wait_for_http(endpoint_url)
        yield endpoint_url


def _wait_for_http(url: str, timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    while True:
        try:
            urllib.request.urlopen(url).close()
            return
        except urllib.error.HTTPError:
            return  # The server answered, if only to refuse an anonymous request.
        except OSError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.2)


@pytest.fixture
def s3_bucket(s3_server: str) -> dict[str, str]:
    """A new, empty bucket for one test, as the settings of the S3 storage adapter."""
    settings = {
        "endpoint_url": s3_server,
        "region": S3_REGION,
        "bucket": f"test-{uuid.uuid4().hex}",
        "access_key_id": S3_ACCESS_KEY,
        "secret_access_key": S3_SECRET_KEY,
    }

    async def create() -> None:
        session = aiobotocore.session.get_session()
        async with session.create_client(
            "s3",
            endpoint_url=settings["endpoint_url"],
            region_name=settings["region"],
            aws_access_key_id=settings["access_key_id"],
            aws_secret_access_key=settings["secret_access_key"],
        ) as client:
            await client.create_bucket(Bucket=settings["bucket"])

    asyncio.run(create())
    return settings
