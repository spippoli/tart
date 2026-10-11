"""Alembic environment: online, async, against `DATABASE_URL`."""

import asyncio

from alembic import context
from geoalchemy2 import alembic_helpers
from sqlalchemy import Connection

from tart.db import Base, create_engine


def _include_object(object_, name, type_, reflected, compare_to) -> bool:
    # Procrastinate's tables are created from its frozen SQL schema, not from the
    # models, so autogenerate must not propose dropping them.
    if type_ == "table" and name and name.startswith("procrastinate_"):
        return False
    return alembic_helpers.include_object(object_, name, type_, reflected, compare_to)


def _run(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        # GeoAlchemy2's hooks, so that autogenerate handles spatial columns and indexes.
        include_object=_include_object,
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
