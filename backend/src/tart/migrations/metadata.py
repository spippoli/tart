"""The migrations' target: every module's tables, and what autogenerate leaves alone."""

from geoalchemy2 import alembic_helpers
from sqlalchemy import MetaData

# Register every module's tables on the metadata.
import tart.archive_persistence.tables
import tart.auth.tables
import tart.media.tables
import tart.rate_limits  # noqa: F401
from tart.db import Base


def metadata() -> MetaData:
    return Base.metadata


def include_object(object_, name, type_, reflected, compare_to) -> bool:
    # Procrastinate's tables are created from its frozen SQL schema, not from the
    # models, so autogenerate must not propose dropping them.
    if type_ == "table" and name and name.startswith("procrastinate_"):
        return False
    return alembic_helpers.include_object(object_, name, type_, reflected, compare_to)
