"""Archive persistence: the PostgreSQL + PostGIS adapter of the archive domain (ADR 0004).

revisions = await write_changeset(engine, changeset, provenance, rules_from_instance(instance))
"""

from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncEngine

from tart.archive.changeset import Changeset
from tart.archive.geometry import Boundary
from tart.archive.revisions import Provenance, Revision
from tart.archive.rules import InstanceRules
from tart.archive.write import apply_changeset
from tart.archive_persistence.store import PostgresArchiveStore
from tart.config import Instance


def rules_from_instance(instance: Instance) -> InstanceRules:
    """What the write operation needs from the Instance configuration."""
    vocabularies = instance.vocabularies
    return InstanceRules(
        boundary=Boundary.from_geojson(instance.boundary),
        time_zone=ZoneInfo(instance.settings.geography.time_zone),
        expression_types={entry.key: entry.retired for entry in vocabularies["expression_types"]},
        surface_types={entry.key: entry.retired for entry in vocabularies["surface_types"]},
        file_licences=frozenset(instance.settings.licenses.files),
    )


async def write_changeset(
    engine: AsyncEngine, changeset: Changeset, provenance: Provenance, rules: InstanceRules
) -> tuple[Revision, ...]:
    """Apply the changeset in one transaction of its own; nothing is stored if it fails."""
    async with engine.begin() as connection:
        return await apply_changeset(PostgresArchiveStore(connection), changeset, provenance, rules)


__all__ = ["PostgresArchiveStore", "rules_from_instance", "write_changeset"]
