"""The port the write operation needs from persistence.

An adapter works inside one transaction, which its caller commits after the write
operation returns, or rolls back when it raises. The port has no way to delete a
record: records leave the database only by Purge (Rights and legal actions).
"""

from collections.abc import Iterable
from typing import Protocol

from tart.archive.codec import Json
from tart.archive.records import Kind, Record, RecordId
from tart.archive.revisions import Provenance, Revision


class ArchiveStore(Protocol):
    async def allocate_id(self, kind: Kind) -> RecordId:
        """A new id, never used before by any record of any kind."""
        ...

    async def allocate_history_event_id(self) -> int:
        """A new History event id, never used before by any event."""
        ...

    async def get(self, record_id: RecordId) -> Record | None:
        """The stored record, or `None` when no record has this id."""
        ...

    async def save(self, record_id: RecordId, record: Record, *, new: bool) -> None:
        """Insert a new record, or replace the stored values of an existing one."""
        ...

    async def add_revision(
        self,
        record_id: RecordId,
        kind: Kind,
        provenance: Provenance,
        changes: tuple[dict[str, Json], ...],
    ) -> Revision: ...

    async def public_records(self, record_ids: Iterable[RecordId]) -> frozenset[RecordId]:
        """Those of the stored records that the public can see."""
        ...

    async def members_of(self, collective_id: RecordId) -> frozenset[RecordId]:
        """The stored Artists that hold a Crew membership in the collective."""
        ...

    async def artworks_signed_with(self, artist_id: RecordId, alias: str) -> frozenset[RecordId]:
        """The stored Artworks with an Attribution to the Artist naming the Alias."""
        ...

    async def documentation_items_of(self, artwork_ids: Iterable[RecordId]) -> frozenset[RecordId]:
        """The stored Documentation items linked to any of the Artworks."""
        ...
