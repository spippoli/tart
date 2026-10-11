"""Alembic migrations, run forward only (ADR 0020), and the startup revision guard.

Migrations run only on request, from `tart migrate` (the in-container step of
`tart upgrade`); `api` and `worker` call `ensure_database_at_head` and refuse to
start when the database revision differs from the code's head.
"""

from pathlib import Path
from types import ModuleType

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Connection

from tart.db import create_engine

DIRECTORY = Path(__file__).parent
TEMPLATE = DIRECTORY / "script.py.mako"


class RevisionMismatchError(RuntimeError):
    def __init__(self, database: str | None, head: str) -> None:
        super().__init__(
            f"database revision {database or '(none)'} differs from the code's head {head}; "
            "run the migrations with `tart upgrade` (`tart migrate` in development)"
        )


def _config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(DIRECTORY))
    return config


def _script() -> ScriptDirectory:
    return ScriptDirectory.from_config(_config())


def head_revision() -> str:
    head = _script().get_current_head()
    assert head is not None, "the migrations have no head"
    return head


def revision_modules() -> list[ModuleType]:
    return [revision.module for revision in _script().walk_revisions()]


def upgrade_to_head() -> None:
    """Apply every pending migration to the database at `DATABASE_URL`."""
    command.upgrade(_config(), "head")


def _current_revision(connection: Connection) -> str | None:
    return MigrationContext.configure(connection).get_current_revision()


async def ensure_database_at_head() -> None:
    """Raise `RevisionMismatchError` unless the database is at the code's head."""
    engine = create_engine()
    try:
        async with engine.connect() as connection:
            current = await connection.run_sync(_current_revision)
    finally:
        await engine.dispose()
    head = head_revision()
    if current != head:
        raise RevisionMismatchError(current, head)
