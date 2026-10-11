"""S3-compatible storage adapter (ADR 0004); Rome uses Hetzner Object Storage.

An object lives at the key `<area>/<key>` of one private bucket, which the
Operator creates without any public access. The adapter never hands out object
URLs, presigned or public: every read goes through the app.

Use it as an async context manager, which opens and closes the client:

    async with S3Storage(endpoint_url=..., region=..., bucket=..., ...) as storage:
        ...
"""

from collections.abc import AsyncIterable, AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from types import TracebackType
from typing import Any, Self

import aiobotocore.session
from aiobotocore.config import AioConfig
from botocore.exceptions import ClientError

from tart.storage import (
    Area,
    ByteRange,
    ObjectExistsError,
    ObjectNotFoundError,
    ObjectStream,
    RangeNotSatisfiableError,
    object_path,
    resolve_range,
)

# Puts larger than one part are sent as a multipart upload, so that memory use
# stays bounded; S3 requires parts of at least 5 MiB, except the last one.
PART_SIZE = 8 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024

_CONFIG = AioConfig(
    # Path-style requests (`<endpoint>/<bucket>/<key>`) work with every
    # S3-compatible service, whatever its DNS setup.
    s3={"addressing_style": "path"},
    # Checksums only where the S3 API requires them: several S3-compatible
    # services refuse the checksums that newer AWS clients send by default.
    request_checksum_calculation="when_required",
    response_checksum_validation="when_required",
    retries={"mode": "standard"},
)


class S3Storage:
    def __init__(
        self,
        *,
        endpoint_url: str,
        region: str,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
    ) -> None:
        self._settings = {
            "endpoint_url": endpoint_url,
            "region_name": region,
            "aws_access_key_id": access_key_id,
            "aws_secret_access_key": secret_access_key,
        }
        self._bucket = bucket
        self._stack = AsyncExitStack()
        self._client: Any = None

    async def __aenter__(self) -> Self:
        session = aiobotocore.session.get_session()
        self._client = await self._stack.enter_async_context(
            session.create_client("s3", config=_CONFIG, **self._settings)
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._stack.aclose()
        self._client = None

    async def put(self, area: Area, key: str, chunks: AsyncIterable[bytes]) -> None:
        name = object_path(area, key)
        if await self._exists(name):
            raise ObjectExistsError(name)
        # Checked, then written: keys are unique by construction, so the check
        # guards against a programming error rather than a race.
        buffer = bytearray()
        upload_id = None
        parts: list[dict[str, Any]] = []
        try:
            async for chunk in chunks:
                buffer += chunk
                while len(buffer) >= PART_SIZE:
                    if upload_id is None:
                        upload = await self._client.create_multipart_upload(
                            Bucket=self._bucket, Key=name
                        )
                        upload_id = upload["UploadId"]
                    parts.append(
                        await self._upload_part(name, upload_id, parts, buffer[:PART_SIZE])
                    )
                    del buffer[:PART_SIZE]
            if upload_id is None:
                await self._client.put_object(Bucket=self._bucket, Key=name, Body=bytes(buffer))
                return
            if buffer:
                parts.append(await self._upload_part(name, upload_id, parts, buffer))
            await self._client.complete_multipart_upload(
                Bucket=self._bucket,
                Key=name,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )
        except BaseException:
            if upload_id is not None:
                await self._client.abort_multipart_upload(
                    Bucket=self._bucket, Key=name, UploadId=upload_id
                )
            raise

    async def _upload_part(
        self, name: str, upload_id: str, parts: list[dict[str, Any]], data: bytearray
    ) -> dict[str, Any]:
        number = len(parts) + 1
        response = await self._client.upload_part(
            Bucket=self._bucket, Key=name, UploadId=upload_id, PartNumber=number, Body=bytes(data)
        )
        return {"PartNumber": number, "ETag": response["ETag"]}

    async def _exists(self, name: str) -> bool:
        try:
            await self._client.head_object(Bucket=self._bucket, Key=name)
        except ClientError as error:
            if _status(error) == 404:
                return False
            raise
        return True

    async def _size(self, name: str) -> int:
        try:
            response = await self._client.head_object(Bucket=self._bucket, Key=name)
        except ClientError as error:
            if _status(error) == 404:
                raise ObjectNotFoundError(name) from None
            raise
        return response["ContentLength"]

    @asynccontextmanager
    async def get(
        self, area: Area, key: str, byte_range: ByteRange | None = None
    ) -> AsyncIterator[ObjectStream]:
        name = object_path(area, key)
        if byte_range is None:
            request = {}
        else:
            end = "" if byte_range.end is None else byte_range.end
            request = {"Range": f"bytes={byte_range.start}-{end}"}
        try:
            response = await self._client.get_object(Bucket=self._bucket, Key=name, **request)
        except ClientError as error:
            if _status(error) == 404:
                raise ObjectNotFoundError(name) from None
            if _status(error) == 416:
                # Also an empty object, which has no byte to start from.
                raise RangeNotSatisfiableError(await self._size(name)) from None
            raise
        body = response["Body"]
        try:
            if "ContentRange" in response:  # "bytes <start>-<end>/<size>"
                size = int(response["ContentRange"].rpartition("/")[2])
            else:
                size = response["ContentLength"]
            start, length = resolve_range(byte_range, size)
            yield ObjectStream(size=size, start=start, length=length, chunks=_read(body))
        finally:
            body.close()

    async def delete(self, area: Area, key: str) -> None:
        await self._client.delete_object(Bucket=self._bucket, Key=object_path(area, key))


def _status(error: ClientError) -> int | None:
    return error.response.get("ResponseMetadata", {}).get("HTTPStatusCode")


async def _read(body: Any) -> AsyncIterator[bytes]:
    while chunk := await body.read(CHUNK_SIZE):
        yield chunk
