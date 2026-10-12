"""Storage port (Foundations spec, 3. Storage and media pipeline; ADR 0004).

Objects are addressed by a key inside one of two areas: `quarantine`, where an
upload waits for the media pipeline, and `permanent`, where the processed
originals and renditions live. The same key in the two areas names two
different objects.

Every object is private and reaches a browser only through the app: whether a
file is public is a database flag, never a property of the stored object.
Objects are immutable: a key is written once and never overwritten, which is
also what lets backups and restores copy objects by key alone.

Adapters: `FilesystemStorage` (the minimal default) and `S3Storage` (any
S3-compatible service). Both map an object to the same `<area>/<key>` path, so
objects can be copied between them unchanged.
"""

import re
from collections.abc import AsyncIterable, AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from tart.config.environment import Environment


class Area(StrEnum):
    QUARANTINE = "quarantine"
    PERMANENT = "permanent"


@dataclass(frozen=True)
class ByteRange:
    """Bytes `start` to `end`, both inclusive as in an HTTP `Range` header.

    `end=None` reads to the end of the object; an `end` past the end is clamped.
    """

    start: int
    end: int | None = None

    def __post_init__(self) -> None:
        if self.start < 0 or (self.end is not None and self.end < self.start):
            raise ValueError(f"invalid byte range: {self.start}-{self.end}")


@dataclass(frozen=True)
class ObjectStream:
    """The bytes of an object, or of a range of it, read in chunks.

    `size` is the size of the whole object; the chunks hold `length` bytes from
    offset `start`.
    """

    size: int
    start: int
    length: int
    chunks: AsyncIterator[bytes]

    def __aiter__(self) -> AsyncIterator[bytes]:
        return self.chunks


class StorageError(Exception):
    pass


class InvalidKeyError(StorageError, ValueError):
    pass


class ObjectNotFoundError(StorageError):
    pass


class ObjectExistsError(StorageError):
    """A put to a key that already holds an object: stored objects are immutable."""


class RangeNotSatisfiableError(StorageError):
    """The range starts at or past the end of the object, whose `size` it carries."""

    def __init__(self, size: int) -> None:
        super().__init__(f"range not satisfiable for an object of {size} bytes")
        self.size = size


class Storage(Protocol):
    async def put(self, area: Area, key: str, chunks: AsyncIterable[bytes]) -> None:
        """Store the chunks as a new object; nothing is stored if they fail midway.

        Raises `ObjectExistsError` when the key already holds an object.
        """
        ...

    def get(
        self, area: Area, key: str, byte_range: ByteRange | None = None
    ) -> AbstractAsyncContextManager[ObjectStream]:
        """Open an object, or a range of it, for streaming; leaving the context closes it.

        Raises `ObjectNotFoundError` or `RangeNotSatisfiableError` on entering.
        """
        ...

    async def delete(self, area: Area, key: str) -> None:
        """Delete an object; deleting a missing object is not an error."""
        ...


# One or more `/`-separated segments of letters, digits, `.`, `_`, and `-`, each
# starting with a letter or a digit: no empty, hidden, `.`, or `..` segment.
_KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*(/[A-Za-z0-9][A-Za-z0-9._-]*)*")


def object_path(area: Area, key: str) -> str:
    """The object's path below the storage root, the same in every adapter."""
    if not _KEY.fullmatch(key):
        raise InvalidKeyError(f"invalid object key: {key!r}")
    return f"{Area(area).value}/{key}"


def resolve_range(byte_range: ByteRange | None, size: int) -> tuple[int, int]:
    """The offset and length that a range selects in an object of `size` bytes."""
    if byte_range is None:
        return 0, size
    if byte_range.start >= size:
        raise RangeNotSatisfiableError(size)
    end = size - 1 if byte_range.end is None else min(byte_range.end, size - 1)
    return byte_range.start, end - byte_range.start + 1


@asynccontextmanager
async def open_storage(environment: Environment) -> AsyncIterator[Storage]:
    """The adapter that `STORAGE_BACKEND` names, open for the life of the service."""
    if environment.STORAGE_BACKEND == "filesystem":
        from tart.storage.filesystem import FilesystemStorage

        yield FilesystemStorage(environment.STORAGE_PATH)
        return
    from tart.storage.s3 import S3Storage

    assert environment.S3_ENDPOINT_URL and environment.S3_ACCESS_KEY_ID
    assert environment.S3_SECRET_ACCESS_KEY and environment.S3_REGION and environment.S3_BUCKET
    async with S3Storage(
        endpoint_url=str(environment.S3_ENDPOINT_URL),
        region=environment.S3_REGION,
        bucket=environment.S3_BUCKET,
        access_key_id=environment.S3_ACCESS_KEY_ID.get_secret_value(),
        secret_access_key=environment.S3_SECRET_ACCESS_KEY.get_secret_value(),
    ) as storage:
        yield storage
