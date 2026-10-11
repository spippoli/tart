"""Contract of the storage port, run against every adapter (Foundations spec, Testing Decisions)."""

import stat
import urllib.error
import urllib.request
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

import pytest

from tart.storage import (
    Area,
    ByteRange,
    InvalidKeyError,
    ObjectExistsError,
    ObjectNotFoundError,
    RangeNotSatisfiableError,
    Storage,
)
from tart.storage.filesystem import FilesystemStorage
from tart.storage.s3 import S3Storage

pytestmark = pytest.mark.anyio

CONTENT = bytes(range(256)) * 1000  # 256,000 bytes, so that reads span several chunks
# Larger than two S3 multipart parts, as a full-size photo can be.
LARGE = bytes(range(251)) * 80_000  # 20,080,000 bytes


async def chunks_of(data: bytes, size: int = 10_000) -> AsyncIterator[bytes]:
    for offset in range(0, len(data), size):
        yield data[offset : offset + size]


async def read(storage: Storage, area: Area, key: str, byte_range: ByteRange | None = None):
    async with storage.get(area, key, byte_range) as stream:
        data = b"".join([chunk async for chunk in stream])
    assert len(data) == stream.length
    return stream, data


# An outsider reads an object without going through the app: True if it gets the bytes.
type OutsiderRead = Callable[[Area, str], bool]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(params=["filesystem", "s3"])
def adapter(request: pytest.FixtureRequest) -> str:
    return request.param


@pytest.fixture
def settings(adapter: str, request: pytest.FixtureRequest) -> dict[str, Any]:
    """The adapter's constructor settings, prepared outside the event loop."""
    if adapter == "filesystem":
        return {"root": request.getfixturevalue("tmp_path") / "media"}
    return request.getfixturevalue("s3_bucket")


@pytest.fixture
async def storage(adapter: str, settings: dict[str, Any]) -> AsyncIterator[Storage]:
    if adapter == "filesystem":
        yield FilesystemStorage(**settings)
        return
    async with S3Storage(**settings) as s3:
        yield s3


@pytest.fixture
def outsider_read(adapter: str, settings: dict[str, Any]) -> OutsiderRead:
    if adapter == "filesystem":
        root: Path = settings["root"]

        def other_user_can_read(area: Area, key: str) -> bool:
            # Another account on the host, or a container running as another user.
            path = root / area / key
            directories = [d for d in path.parents if d.is_relative_to(root)]
            readable = path.stat().st_mode & (stat.S_IRGRP | stat.S_IROTH)
            reachable = all(d.stat().st_mode & (stat.S_IXGRP | stat.S_IXOTH) for d in directories)
            return bool(readable) and reachable

        return other_user_can_read

    def anonymous_http_get_succeeds(area: Area, key: str) -> bool:
        url = f"{settings['endpoint_url']}/{settings['bucket']}/{area}/{key}"
        try:
            with urllib.request.urlopen(url) as response:
                response.read()
        except urllib.error.HTTPError as error:
            assert error.code == 403
            return False
        return True

    return anonymous_http_get_succeeds


async def test_criterion_21_a_stored_object_is_private_and_read_only_through_the_app(
    storage: Storage, outsider_read: OutsiderRead
) -> None:
    for area in Area:
        await storage.put(area, "uploads/photo.jpg", chunks_of(CONTENT))

        _, data = await read(storage, area, "uploads/photo.jpg")
        assert data == CONTENT
        assert not outsider_read(area, "uploads/photo.jpg")


async def test_put_then_get_streams_the_whole_object(storage: Storage) -> None:
    await storage.put(Area.PERMANENT, "a/b/original", chunks_of(CONTENT))

    stream, data = await read(storage, Area.PERMANENT, "a/b/original")

    assert data == CONTENT
    assert (stream.size, stream.start, stream.length) == (len(CONTENT), 0, len(CONTENT))


async def test_an_empty_object_can_be_stored_and_read(storage: Storage) -> None:
    await storage.put(Area.PERMANENT, "empty", chunks_of(b""))

    stream, data = await read(storage, Area.PERMANENT, "empty")

    assert (data, stream.size, stream.length) == (b"", 0, 0)


async def test_a_large_object_is_streamed_in_and_out(storage: Storage) -> None:
    await storage.put(Area.QUARANTINE, "large", chunks_of(LARGE, size=1024 * 1024))

    assert (await read(storage, Area.QUARANTINE, "large"))[1] == LARGE
    across_a_part_boundary = ByteRange(8 * 1024 * 1024 - 10, 8 * 1024 * 1024 + 9)
    assert (await read(storage, Area.QUARANTINE, "large", across_a_part_boundary))[1] == (
        LARGE[8 * 1024 * 1024 - 10 : 8 * 1024 * 1024 + 10]
    )


@pytest.mark.parametrize(
    ("byte_range", "start", "end"),
    [
        (ByteRange(0, 0), 0, 0),
        (ByteRange(100, 199), 100, 199),
        (ByteRange(70_000), 70_000, len(CONTENT) - 1),
        (ByteRange(len(CONTENT) - 1, len(CONTENT) - 1), len(CONTENT) - 1, len(CONTENT) - 1),
        (ByteRange(250_000, 10_000_000), 250_000, len(CONTENT) - 1),  # end clamped
    ],
)
async def test_get_streams_a_byte_range(
    storage: Storage, byte_range: ByteRange, start: int, end: int
) -> None:
    await storage.put(Area.PERMANENT, "ranged", chunks_of(CONTENT))

    stream, data = await read(storage, Area.PERMANENT, "ranged", byte_range)

    assert data == CONTENT[start : end + 1]
    assert (stream.size, stream.start, stream.length) == (len(CONTENT), start, end - start + 1)


@pytest.mark.parametrize("start", [len(CONTENT), len(CONTENT) + 10])
async def test_a_range_past_the_end_is_not_satisfiable(storage: Storage, start: int) -> None:
    await storage.put(Area.PERMANENT, "ranged", chunks_of(CONTENT))

    with pytest.raises(RangeNotSatisfiableError) as raised:
        await read(storage, Area.PERMANENT, "ranged", ByteRange(start))

    assert raised.value.size == len(CONTENT)


async def test_a_missing_object_is_not_found(storage: Storage) -> None:
    with pytest.raises(ObjectNotFoundError):
        await read(storage, Area.PERMANENT, "missing")


async def test_quarantine_and_permanent_are_separate_areas(storage: Storage) -> None:
    await storage.put(Area.QUARANTINE, "upload", chunks_of(b"quarantined"))

    with pytest.raises(ObjectNotFoundError):
        await read(storage, Area.PERMANENT, "upload")

    await storage.put(Area.PERMANENT, "upload", chunks_of(b"processed"))
    assert (await read(storage, Area.QUARANTINE, "upload"))[1] == b"quarantined"
    assert (await read(storage, Area.PERMANENT, "upload"))[1] == b"processed"

    await storage.delete(Area.QUARANTINE, "upload")
    with pytest.raises(ObjectNotFoundError):
        await read(storage, Area.QUARANTINE, "upload")
    assert (await read(storage, Area.PERMANENT, "upload"))[1] == b"processed"


async def test_a_stored_object_is_never_overwritten(storage: Storage) -> None:
    await storage.put(Area.PERMANENT, "immutable", chunks_of(b"first"))

    with pytest.raises(ObjectExistsError):
        await storage.put(Area.PERMANENT, "immutable", chunks_of(b"second"))

    assert (await read(storage, Area.PERMANENT, "immutable"))[1] == b"first"


@pytest.mark.parametrize("sent", [CONTENT, LARGE])
async def test_a_put_that_fails_midway_stores_nothing(storage: Storage, sent: bytes) -> None:
    async def failing() -> AsyncIterator[bytes]:
        async for chunk in chunks_of(sent, size=1024 * 1024):
            yield chunk
        raise ConnectionResetError("client went away")

    with pytest.raises(ConnectionResetError):
        await storage.put(Area.QUARANTINE, "partial", failing())

    with pytest.raises(ObjectNotFoundError):
        await read(storage, Area.QUARANTINE, "partial")
    # The key is still free.
    await storage.put(Area.QUARANTINE, "partial", chunks_of(b"retried"))


async def test_delete_removes_the_object_and_tolerates_a_missing_one(storage: Storage) -> None:
    await storage.put(Area.PERMANENT, "gone", chunks_of(CONTENT))

    await storage.delete(Area.PERMANENT, "gone")
    await storage.delete(Area.PERMANENT, "gone")

    with pytest.raises(ObjectNotFoundError):
        await read(storage, Area.PERMANENT, "gone")


@pytest.mark.parametrize(
    "key", ["", "/abs", "a//b", "../escape", "a/../b", "a/./b", ".hidden", "a/", "spa ce", "è"]
)
async def test_an_unsafe_key_is_refused(storage: Storage, key: str) -> None:
    with pytest.raises(InvalidKeyError):
        await storage.put(Area.PERMANENT, key, chunks_of(b"x"))
    with pytest.raises(InvalidKeyError):
        await read(storage, Area.PERMANENT, key)
    with pytest.raises(InvalidKeyError):
        await storage.delete(Area.PERMANENT, key)
