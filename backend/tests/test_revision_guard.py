"""Operations and portability, acceptance criterion 6.

`api` and `worker` refuse to start when the database revision differs from the
code's Alembic head, and no service runs migrations at startup.
"""

import subprocess
import sys

import pytest
from conftest import execute, fetch_value
from fastapi.testclient import TestClient

from tart.api.app import create_app
from tart.cli import main as run_cli

AHEAD_OF_THE_CODE = "ffffffffffff"


def _has_alembic_version(dsn: str) -> bool:
    return fetch_value(dsn, "SELECT to_regclass('alembic_version') IS NOT NULL")  # type: ignore[return-value]


def _start_api() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "tart.api.app:create_app",
            "--factory",
            "--port",
            "0",
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )


def _start_worker() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "tart.worker"], capture_output=True, text=True, timeout=20
    )


@pytest.fixture
def database_behind(database: str) -> str:
    """An empty database: no migration has ever run."""
    return database


@pytest.fixture
def database_ahead(database: str) -> str:
    """A database stamped with a revision the code does not know."""
    run_cli(["migrate"])
    execute(database, f"UPDATE alembic_version SET version_num = '{AHEAD_OF_THE_CODE}'")
    return database


@pytest.mark.parametrize("state", ["database_behind", "database_ahead"])
def test_api_refuses_to_start_when_the_revision_differs(
    state: str, request: pytest.FixtureRequest
) -> None:
    dsn = request.getfixturevalue(state)

    result = _start_api()

    assert result.returncode != 0
    assert "revision" in result.stderr
    assert "Application startup failed" in result.stderr
    if state == "database_behind":
        assert not _has_alembic_version(dsn), "the api ran migrations at startup"


@pytest.mark.parametrize("state", ["database_behind", "database_ahead"])
def test_worker_refuses_to_start_when_the_revision_differs(
    state: str, request: pytest.FixtureRequest
) -> None:
    dsn = request.getfixturevalue(state)

    result = _start_worker()

    assert result.returncode != 0
    assert "revision" in result.stderr
    if state == "database_behind":
        assert not _has_alembic_version(dsn), "the worker ran migrations at startup"


def test_api_starts_when_the_database_is_at_the_head(database: str) -> None:
    run_cli(["migrate"])

    with TestClient(create_app()) as client:
        assert client.get("/api/config").status_code == 200
