"""Local-filesystem storage adapter, the minimal default (ADR 0004).

An object lives at `<root>/<area>/<key>`. Files and directories are readable by
their owner only, so nothing but the app's own user reads them; the storage
root must not be mounted in a container that serves files, such as Caddy.
"""

import asyncio
import os
import uuid
from collections.abc import AsyncIterable, AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import BinaryIO

from tart.storage import (
    Area,
    ByteRange,
    ObjectExistsError,
    ObjectNotFoundError,
    ObjectStream,
    object_path,
    resolve_range,
)

CHUNK_SIZE = 1024 * 1024
FILE_MODE = 0o600
DIRECTORY_MODE = 0o700
# Puts are written here first and linked into their area once complete, so
# that a failed put leaves no object behind.
PARTIAL = ".partial"


class FilesystemStorage:
    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def _path(self, area: Area, key: str) -> Path:
        return self._root / object_path(area, key)

    async def put(self, area: Area, key: str, chunks: AsyncIterable[bytes]) -> None:
        path = self._path(area, key)
        if path.exists():
            raise ObjectExistsError(f"{area}/{key}")
        partial = self._root / PARTIAL / uuid.uuid4().hex
        await asyncio.to_thread(_make_directories, partial.parent)
        descriptor = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL, FILE_MODE)
        try:
            with os.fdopen(descriptor, "wb") as file:
                async for chunk in chunks:
                    await asyncio.to_thread(file.write, chunk)
                await asyncio.to_thread(_flush, file)
            await asyncio.to_thread(_make_directories, path.parent)
            try:
                os.link(partial, path)  # fails, unlike a rename, if the key is taken
            except FileExistsError:
                raise ObjectExistsError(f"{area}/{key}") from None
        finally:
            partial.unlink(missing_ok=True)

    @asynccontextmanager
    async def get(
        self, area: Area, key: str, byte_range: ByteRange | None = None
    ) -> AsyncIterator[ObjectStream]:
        path = self._path(area, key)
        try:
            file = await asyncio.to_thread(path.open, "rb")
        except FileNotFoundError:
            raise ObjectNotFoundError(f"{area}/{key}") from None
        try:
            size = os.fstat(file.fileno()).st_size
            start, length = resolve_range(byte_range, size)
            await asyncio.to_thread(file.seek, start)
            yield ObjectStream(size=size, start=start, length=length, chunks=_read(file, length))
        finally:
            await asyncio.to_thread(file.close)

    async def delete(self, area: Area, key: str) -> None:
        await asyncio.to_thread(self._path(area, key).unlink, missing_ok=True)


def _make_directories(path: Path) -> None:
    # `mkdir(parents=True)` would create the parents with the default mode.
    for directory in [*reversed(path.parents), path]:
        if not directory.exists():
            directory.mkdir(mode=DIRECTORY_MODE, exist_ok=True)


def _flush(file: BinaryIO) -> None:
    file.flush()
    os.fsync(file.fileno())


async def _read(file: BinaryIO, length: int) -> AsyncIterator[bytes]:
    remaining = length
    while remaining > 0:
        chunk = await asyncio.to_thread(file.read, min(CHUNK_SIZE, remaining))
        if not chunk:
            return
        remaining -= len(chunk)
        yield chunk
