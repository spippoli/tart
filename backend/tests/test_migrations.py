import asyncio
import subprocess

from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from conftest import fetch_value
from sqlalchemy import Connection

from tart import migrations
from tart.cli import main as run_cli
from tart.db import create_engine
from tart.migrations.metadata import include_object, metadata


def _revision(dsn: str) -> object:
    return fetch_value(dsn, "SELECT version_num FROM alembic_version")


def test_tart_migrate_brings_an_empty_database_to_the_code_head(database: str) -> None:
    assert run_cli(["migrate"]) == 0

    assert _revision(database) == migrations.head_revision()
    assert fetch_value(database, "SELECT extname FROM pg_extension WHERE extname = 'postgis'")


def test_tart_migrate_is_a_no_op_on_a_database_at_the_head(database: str) -> None:
    run_cli(["migrate"])

    assert run_cli(["migrate"]) == 0
    assert _revision(database) == migrations.head_revision()


def test_the_tart_command_is_installed_with_its_subcommands() -> None:
    result = subprocess.run(["tart", "--help"], capture_output=True, text=True, check=True)

    assert "migrate" in result.stdout


def test_an_unknown_subcommand_is_a_usage_error() -> None:
    result = subprocess.run(["tart", "no-such-command"], capture_output=True, text=True)

    assert result.returncode == 2


# Operations and portability, acceptance criterion 7: migrations run forward only.
def test_no_migration_implements_downgrade() -> None:
    modules = migrations.revision_modules()

    assert modules, "expected at least one migration"
    for module in modules:
        assert not hasattr(module, "downgrade"), module.__file__
    # The template that `alembic revision` renders new migrations from.
    assert "downgrade" not in migrations.TEMPLATE.read_text()


def test_the_migrations_create_the_tables_the_code_declares(migrated_database: str) -> None:
    def differences(connection: Connection) -> list[object]:
        context = MigrationContext.configure(connection, opts={"include_object": include_object})
        return compare_metadata(context, metadata())

    async def run() -> list[object]:
        engine = create_engine(migrated_database)
        try:
            async with engine.connect() as connection:
                return await connection.run_sync(differences)
        finally:
            await engine.dispose()

    assert asyncio.run(run()) == []
