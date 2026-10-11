"""Alembic environment: online, async, against `DATABASE_URL`."""

import asyncio

from alembic import context
from geoalchemy2 import alembic_helpers
from sqlalchemy import Connection

from tart.db import create_engine
from tart.migrations.metadata import include_object, metadata


def _run(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=metadata(),
        # GeoAlchemy2's hooks, so that autogenerate handles spatial columns and indexes.
        include_object=include_object,
        process_revision_directives=alembic_helpers.writer,
        render_item=alembic_helpers.render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_online() -> None:
    engine = create_engine()
    try:
        async with engine.connect() as connection:
            await connection.run_sync(_run)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    raise SystemExit("Offline (--sql) migrations are not supported.")
asyncio.run(_run_online())
