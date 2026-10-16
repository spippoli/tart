"""`/api/media`: uploads and the files derived from them (Foundations spec, 3. Storage and
media pipeline).

    POST /api/media                       one file, multipart; 202 while it is processed
    GET  /api/media/{id}                  its state, for its Submitter and Moderators
    GET  /api/media/{id}/{rendition}      a WebP rendition; the original is never served

The upload streams into quarantine as it arrives: the file's size is counted on the way,
so a file over `max_upload_mb` or a second file stops the request and nothing is stored.
Refusals carry a translatable error code, `{"code": ...}`.
"""

import uuid
from collections.abc import AsyncIterable, AsyncIterator
from contextlib import AsyncExitStack
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from procrastinate import App
from pydantic import BaseModel
from python_multipart.exceptions import MultipartParseError
from python_multipart.multipart import MultipartParser, parse_options_header
from sqlalchemy.ext.asyncio import AsyncEngine

from tart import rate_limits
from tart.api.auth import (
    SIGN_IN_REQUIRED,
    Clock,
    Error,
    current_user,
    get_clock,
    get_configuration,
    get_engine,
    get_jobs,
    get_key,
)
from tart.api.limits import LimitedError, limited
from tart.auth.sessions import SessionUser
from tart.config import Configuration
from tart.jobs import PROCESS_UPLOAD
from tart.media import (
    FILE_MISSING,
    FILE_TOO_LARGE,
    MULTIPART_MARGIN_MB,
    ONE_FILE_PER_REQUEST,
    UPLOAD_NOT_FOUND,
    Rendition,
    quarantine_key,
    rendition_key,
    uploads,
)
from tart.moderation_persistence import limits
from tart.storage import Area, ObjectNotFoundError, Storage

router = APIRouter(prefix="/api/media")

MIB = 1024 * 1024
PUBLIC_CACHE = "public, max-age=3600"
"""Public renditions: a takedown reaches intermediate caches within the hour."""
PRIVATE_CACHE = "private, no-store"


def get_storage(request: Request) -> Storage:
    return request.app.state.storage


class Refused(Exception):
    def __init__(self, code: str, status: int) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


class _OneFile:
    """Reads a multipart body and passes on the bytes of its one file part.

    Other parts are skipped unread into memory. A second file part, or a file past the
    limit, raises `Refused` from inside the stream, which aborts the storage put.
    """

    def __init__(self, boundary: bytes, limit: int) -> None:
        self.limit = limit
        self.files = 0
        self.size = 0
        self._in_file = False
        self._field = b""
        self._headers: dict[bytes, bytes] = {}
        self._pending: list[bytes] = []
        self._parser = MultipartParser(
            boundary,
            {
                "on_part_begin": self._part_begin,
                "on_header_field": self._header_field,
                "on_header_value": self._header_value,
                "on_headers_finished": self._headers_finished,
                "on_part_data": self._part_data,
            },
        )

    def _part_begin(self) -> None:
        self._in_file = False
        self._headers = {}

    def _header_field(self, data: bytes, start: int, end: int) -> None:
        self._field = data[start:end].lower()

    def _header_value(self, data: bytes, start: int, end: int) -> None:
        self._headers[self._field] = self._headers.get(self._field, b"") + data[start:end]

    def _headers_finished(self) -> None:
        _, params = parse_options_header(self._headers.get(b"content-disposition"))
        if b"filename" in params:
            self.files += 1
            if self.files > 1:
                raise Refused(ONE_FILE_PER_REQUEST, 400)
            self._in_file = True

    def _part_data(self, data: bytes, start: int, end: int) -> None:
        if not self._in_file:
            return
        self.size += end - start
        if self.size > self.limit:
            raise Refused(FILE_TOO_LARGE, 413)
        self._pending.append(data[start:end])

    async def chunks(self, body: AsyncIterable[bytes]) -> AsyncIterator[bytes]:
        try:
            async for chunk in body:
                self._parser.write(chunk)
                if self._pending:
                    yield b"".join(self._pending)
                    self._pending.clear()
            self._parser.finalize()
        except MultipartParseError:
            raise Refused(FILE_MISSING, 400) from None
        if self._pending:
            yield b"".join(self._pending)
        if self.files == 0:
            raise Refused(FILE_MISSING, 400)


class Size(BaseModel):
    width: int
    height: int


class Suggestions(BaseModel):
    """From the file's EXIF, only to prefill the form; never a stored Location."""

    observed_date: str | None
    """The capture date, `YYYY-MM-DD`."""
    point: tuple[float, float] | None
    """Where the camera was, `[longitude, latitude]`."""


class UploadState(BaseModel):
    id: uuid.UUID
    status: Literal["processing", "ready", "rejected", "deleted"]
    """`deleted`: the file went with the media of a rejected or retracted Submission."""
    error: str | None = None
    """Why the file was refused: `file_type_unsupported`, `file_unreadable`, `image_too_large`."""
    format: Literal["jpeg", "png", "webp", "avif", "heic", "pdf"] | None = None
    renditions: dict[Rendition, Size] | None = None
    suggestions: Suggestions | None = None
    """For the User who uploaded the file only."""


def _refused(code: str, status: int) -> JSONResponse:
    return JSONResponse({"code": code}, status_code=status)


_ERRORS = {
    401: {"model": Error},
    400: {"model": Error, "description": "`file_missing`, `one_file_per_request`"},
    413: {"model": Error, "description": "`file_too_large`"},
    429: {
        "model": LimitedError,
        "description": "`moderation.uploads_limited`: 100 files or 1 GB in 24 hours; Moderators "
        "are exempt.",
    },
}


@router.post("", status_code=202, response_model=UploadState, responses=_ERRORS)
async def upload_file(
    request: Request,
    user: Annotated[SessionUser | None, Depends(current_user)],
    configuration: Annotated[Configuration, Depends(get_configuration)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    storage: Annotated[Storage, Depends(get_storage)],
    jobs: Annotated[App, Depends(get_jobs)],
    clock: Annotated[Clock, Depends(get_clock)],
    key: Annotated[bytes, Depends(get_key)],
) -> UploadState | JSONResponse:
    """Upload one file, in a multipart field (any name), at most `max_upload_mb`.

    Each User may upload 100 files and 1 GB in 24 hours, rejected files included; the size
    counted is the one the request declares, or the per-file limit when it declares none.
    """
    if user is None:
        return _refused(SIGN_IN_REQUIRED, 401)
    media = configuration.instance.settings.media
    limit = media.max_upload_mb * MIB
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit + MULTIPART_MARGIN_MB * MIB:
        return _refused(FILE_TOO_LARGE, 413)
    kind, params = parse_options_header(request.headers.get("content-type"))
    if kind != b"multipart/form-data" or not params.get(b"boundary"):
        return _refused(FILE_MISSING, 400)

    now = clock()
    async with engine.begin() as connection:
        if not user.moderator:
            cost = max(int(declared), 1) if declared.isdigit() else limit
            wait = await rate_limits.hit(
                connection,
                [
                    (limits.UPLOAD_FILES, str(user.id)),
                    (limits.UPLOAD_BYTES, str(user.id), cost),
                ],
                now,
                key,
            )
            if wait is not None:
                return limited(limits.UPLOADS_LIMITED, wait)
        upload_id = await uploads.create(connection, user.id, now)
    reader = _OneFile(params[b"boundary"], limit)
    try:
        await storage.put(
            Area.QUARANTINE, quarantine_key(str(upload_id)), reader.chunks(request.stream())
        )
    except BaseException as error:
        async with engine.begin() as connection:
            await uploads.discard(connection, upload_id)
        if isinstance(error, Refused):
            return _refused(error.code, error.status)
        raise
    async with engine.begin() as connection:
        await uploads.received(connection, upload_id, reader.size)
    await jobs.configure_task(PROCESS_UPLOAD).defer_async(
        upload_id=str(upload_id), cap=media.public_rendition_max_px
    )
    return UploadState(id=upload_id, status="processing")


def _state_of(upload: uploads.Upload) -> str:
    return "deleted" if upload.deleted_at is not None else upload.status


def _visible_to(user: SessionUser | None, upload: uploads.Upload) -> bool:
    return user is not None and (user.id == upload.user_id or user.moderator)


@router.get("/{upload_id}", response_model=UploadState, responses={404: {"model": Error}})
async def upload_state(
    upload_id: uuid.UUID,
    user: Annotated[SessionUser | None, Depends(current_user)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
) -> UploadState | JSONResponse:
    """An upload's processing state, for the User who uploaded it and for Moderators."""
    async with engine.begin() as connection:
        upload = await uploads.read(connection, upload_id)
    if upload is None or not _visible_to(user, upload):
        return _refused(UPLOAD_NOT_FOUND, 404)
    own = user is not None and user.id == upload.user_id
    renditions = upload.renditions or {}
    return UploadState.model_validate(
        {
            "id": upload.id,
            "status": _state_of(upload),
            "error": upload.error,
            "format": upload.format,
            "renditions": {r: {"width": w, "height": h} for r, (w, h) in renditions.items()}
            or None,
            "suggestions": upload.suggestions if own else None,
        }
    )


@router.get(
    "/{upload_id}/{rendition}",
    response_class=Response,
    responses={
        200: {"content": {"image/webp": {}}, "description": "The rendition."},
        304: {"description": "The rendition has not changed."},
        404: {"model": Error},
    },
)
async def rendition_file(
    upload_id: uuid.UUID,
    rendition: Rendition,
    request: Request,
    user: Annotated[SessionUser | None, Depends(current_user)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    storage: Annotated[Storage, Depends(get_storage)],
) -> Response:
    """A rendition: public once its Documentation item is approved, else only for the
    User who uploaded it and for Moderators."""
    async with engine.begin() as connection:
        upload = await uploads.read(connection, upload_id)
        public = upload is not None and await uploads.is_public(connection, upload_id)
    if (
        upload is None
        or upload.status != "ready"
        or upload.deleted_at is not None
        or not (public or _visible_to(user, upload))
    ):
        return _refused(UPLOAD_NOT_FOUND, 404)
    # Objects are immutable, so the key names the content.
    headers = {
        "Cache-Control": PUBLIC_CACHE if public else PRIVATE_CACHE,
        "ETag": f'"{upload_id}-{rendition.value}"',
        "X-Content-Type-Options": "nosniff",
    }
    if request.headers.get("if-none-match") == headers["ETag"]:
        return Response(status_code=304, headers=headers)
    stack = AsyncExitStack()
    try:
        stream = await stack.enter_async_context(
            storage.get(Area.PERMANENT, rendition_key(str(upload_id), rendition))
        )
    except ObjectNotFoundError:
        await stack.aclose()
        return _refused(UPLOAD_NOT_FOUND, 404)

    async def body() -> AsyncIterator[bytes]:
        try:
            async for chunk in stream:
                yield chunk
        finally:
            await stack.aclose()

    headers["Content-Length"] = str(stream.length)
    return StreamingResponse(body(), media_type="image/webp", headers=headers)
