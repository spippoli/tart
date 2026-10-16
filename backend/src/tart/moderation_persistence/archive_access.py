"""What moderation reads from the archive, and the dry run of a write.

The write operation is the only way records change (ADR 0002); this module only reads
the state of a target record and the Revisions after a Base revision, and runs the write
operation inside a savepoint it always rolls back.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncConnection

from tart.archive.changeset import Changeset
from tart.archive.records import Kind
from tart.archive.revisions import Provenance
from tart.archive.rules import InstanceRules
from tart.archive.write import apply_changeset
from tart.archive_persistence import PostgresArchiveStore
from tart.archive_persistence import tables as t
from tart.moderation import RecordChange, TargetState
from tart.moderation.outdated import changes_of


async def target_state(connection: AsyncConnection, record_id: int) -> TargetState | None:
    """The target's visibility and latest Revision; `None` when no such record exists."""
    row = (
        await connection.execute(
            select(t.record.c.withdrawn_at, t.record.c.merged_into).where(
                t.record.c.id == record_id
            )
        )
    ).one_or_none()
    if row is None:
        return None
    latest = await connection.scalar(
        select(func.max(t.revision.c.id)).where(t.revision.c.record_id == record_id)
    )
    # Notices belong to the Rights and legal actions spec; until they exist none is open.
    return TargetState(
        record_id,
        latest,
        withdrawn=row.withdrawn_at is not None,
        merged_into=row.merged_into,
        open_notice=False,
    )


async def changes_since(
    connection: AsyncConnection, record_id: int, kind: Kind, after_revision: int
) -> list[RecordChange]:
    """The fields and items changed by the record's Revisions after the given one."""
    rows = await connection.execute(
        select(t.revision.c.id, t.revision.c.changes)
        .where(t.revision.c.record_id == record_id, t.revision.c.id > after_revision)
        .order_by(t.revision.c.id)
    )
    return [change for row in rows for change in changes_of(kind, row.id, row.changes)]


async def dry_run(
    connection: AsyncConnection, changeset: Changeset, provenance: Provenance, rules: InstanceRules
) -> None:
    """Apply the changeset to see whether the archive's rules accept it, then roll it back.
    The write operation's `ArchiveRuleViolation` is the answer."""
    savepoint = await connection.begin_nested()
    try:
        await apply_changeset(PostgresArchiveStore(connection), changeset, provenance, rules)
    finally:
        await savepoint.rollback()
