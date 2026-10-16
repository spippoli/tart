"""The configuration checks that need the database (Foundations spec, 1. Instance configuration).

`tart config check --database` and startup run them after the files are valid:
a vocabulary key stored in the database must still be in its file (retired or
not), and `terms.version` may not go below the highest version already accepted.
They also report warnings, which never fail: about the Moderators (`tart.auth.operator`).

The tables that store vocabulary keys are added by later tickets; each one registers
its column here, in `VOCABULARY_COLUMNS`, in the same change that creates it.
"""

from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from tart.auth.operator import moderator_warnings
from tart.config.loader import Instance, Issue
from tart.db import create_engine


@dataclass(frozen=True)
class Column:
    table: str
    column: str


VOCABULARY_COLUMNS: dict[str, tuple[Column, ...]] = {
    "expression_types": (Column("artwork", "expression_types"),),
    "surface_types": (Column("location", "surface_type"),),
}
"""By vocabulary name, the columns that store its keys (a text or text-array column)."""

TERMS_ACCEPTANCE_COLUMN: Column | None = Column("user_terms_acceptance", "version")
"""The integer column that records which `terms.version` a User accepted."""


@dataclass(frozen=True)
class DatabaseCheck:
    issues: list[Issue] = field(default_factory=list)
    """What makes the configuration invalid against this database."""
    warnings: list[str] = field(default_factory=list)
    """What the Operator should know, without failing."""


async def _keys_in_use(connection: AsyncConnection, column: Column) -> set[str]:
    # Identifiers come from the registry above, never from input.
    result = await connection.execute(
        text(
            f"SELECT DISTINCT k FROM {column.table}, "
            f"unnest(CAST(ARRAY[{column.column}] AS text[])) AS k WHERE k IS NOT NULL"
        )
    )
    return set(result.scalars())


async def _check(connection: AsyncConnection, instance: Instance) -> DatabaseCheck:
    issues: list[Issue] = []
    for name, columns in VOCABULARY_COLUMNS.items():
        known = {entry.key for entry in instance.vocabularies[name]}
        for column in columns:
            for key in sorted(await _keys_in_use(connection, column) - known):
                issues.append(
                    Issue(
                        f"vocabularies/{name}.toml",
                        "entries",
                        f"the key {key!r} is used in the database ({column.table}) "
                        "but is not in the file; retire an entry instead of removing it",
                    )
                )
    if TERMS_ACCEPTANCE_COLUMN is not None:
        column = TERMS_ACCEPTANCE_COLUMN
        accepted = await connection.scalar(text(f"SELECT max({column.column}) FROM {column.table}"))
        version = instance.settings.terms.version
        if accepted is not None and version < accepted:
            issues.append(
                Issue(
                    "instance.toml",
                    "terms.version",
                    f"is {version}, lower than version {accepted} that Users already accepted",
                )
            )
    warnings = await moderator_warnings(connection, instance.settings.community.self_approval)
    return DatabaseCheck(issues, warnings)


async def check_database(instance: Instance) -> DatabaseCheck:
    """The database issues and warnings of a valid configuration, against the database
    at `DATABASE_URL`."""
    engine = create_engine()
    try:
        async with engine.connect() as connection:
            return await _check(connection, instance)
    finally:
        await engine.dispose()
