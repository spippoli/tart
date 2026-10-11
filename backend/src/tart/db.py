"""Database access: SQLAlchemy 2.0 async with GeoAlchemy2 on PostgreSQL + PostGIS (ADR 0004)."""

import os

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# Stable constraint names, so that migrations can refer to them.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class of every mapped table; its metadata is the migrations' target."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def database_url() -> str:
    """The `DATABASE_URL` environment variable, e.g. `postgresql+asyncpg://user:pw@db/tart`."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return url


def create_engine(url: str | None = None) -> AsyncEngine:
    return create_async_engine(url or database_url())
