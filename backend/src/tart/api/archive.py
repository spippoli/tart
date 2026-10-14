"""`/api/archive`: the public views of Archive records (archive-records spec, Public record
pages and Visibility).

    GET /api/archive/{kind}/{id}              the record's view
    GET /api/archive/{kind}/{id}/revisions    its Revisions, most recent first
    GET /api/archive/{kind}?page=N            an index, by name (Artists, Sites, Areas, Series)

`{kind}` is `artworks`, `artists`, `locations`, `sites`, `areas`, `series`, `sources`,
or `documents`. Only the id resolves a record; the view carries its canonical `path`
segment, and the page answers 301 to it. A merged duplicate or a retired
Documentation item answers 301 to the surviving record's view, never through a chain;
a withdrawn record answers 410, except to Moderators; an unknown id, or one of
another kind, answers 404. Refusals carry a translatable error code, `{"code": ...}`.
"""

from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncEngine

from tart.api.auth import Error, current_user, get_engine
from tart.archive import Kind
from tart.archive_read import (
    Reader,
    RecordMergedError,
    RecordNotFoundError,
    RecordWithdrawnError,
    Viewer,
)
from tart.archive_read import views as v
from tart.auth.sessions import SessionUser

router = APIRouter(prefix="/api/archive")

RECORD_NOT_FOUND = "record_not_found"
RECORD_WITHDRAWN = "record_withdrawn"

SEGMENTS = {
    Kind.ARTWORK: "artworks",
    Kind.ARTIST: "artists",
    Kind.LOCATION: "locations",
    Kind.SITE: "sites",
    Kind.AREA: "areas",
    Kind.SERIES: "series",
    Kind.SOURCE: "sources",
    Kind.DOCUMENTATION_ITEM: "documents",
}
_VIEWS: dict[Kind, type] = {
    Kind.ARTWORK: v.ArtworkView,
    Kind.ARTIST: v.ArtistView,
    Kind.LOCATION: v.LocationView,
    Kind.SITE: v.PlaceView,
    Kind.AREA: v.PlaceView,
    Kind.SERIES: v.PlaceView,
    Kind.SOURCE: v.SourceView,
    Kind.DOCUMENTATION_ITEM: v.DocumentationItemView,
}
_ERRORS: dict[int | str, dict[str, Any]] = {
    301: {"description": "A merged duplicate: the surviving record's view."},
    404: {"model": Error, "description": "`record_not_found`"},
    410: {"model": Error, "description": "`record_withdrawn`"},
}

type Caller = SessionUser | None


async def _read[T](
    engine: AsyncEngine,
    user: Caller,
    kind: Kind,
    read: Callable[[Reader], Awaitable[T]],
    suffix: str = "",
) -> T | JSONResponse | RedirectResponse:
    viewer = Viewer(moderator=user is not None and user.moderator)
    try:
        async with engine.connect() as connection:
            return await read(Reader(connection, viewer))
    except RecordNotFoundError:
        return JSONResponse({"code": RECORD_NOT_FOUND}, status_code=404)
    except RecordWithdrawnError:
        return JSONResponse({"code": RECORD_WITHDRAWN}, status_code=410)
    except RecordMergedError as merged:
        return RedirectResponse(
            f"/api/archive/{SEGMENTS[kind]}/{merged.target}{suffix}", status_code=301
        )


def _register(kind: Kind) -> None:
    segment = SEGMENTS[kind]
    label = segment.rstrip("s") if kind is not Kind.SERIES else "series"

    async def view(
        record_id: int,
        user: Annotated[Caller, Depends(current_user)],
        engine: Annotated[AsyncEngine, Depends(get_engine)],
    ) -> Any:
        return await _read(engine, user, kind, lambda reader: reader.view(kind, record_id))

    async def revisions(
        record_id: int,
        user: Annotated[Caller, Depends(current_user)],
        engine: Annotated[AsyncEngine, Depends(get_engine)],
    ) -> Any:
        return await _read(engine, user, kind, lambda reader: reader.revisions(kind, record_id))

    router.add_api_route(
        f"/{segment}/{{record_id}}",
        view,
        methods=["GET"],
        response_model=_VIEWS[kind],
        responses=_ERRORS,
        name=f"{label}_view",
        summary=f"The view of a {kind.value.replace('_', ' ')}",
    )
    router.add_api_route(
        f"/{segment}/{{record_id}}/revisions",
        revisions,
        methods=["GET"],
        response_model=v.RevisionsView,
        responses={404: _ERRORS[404], 410: _ERRORS[410]},
        name=f"{label}_revisions",
        summary=f"The Revisions of a {kind.value.replace('_', ' ')}",
    )
    if kind in (Kind.ARTIST, Kind.SITE, Kind.AREA, Kind.SERIES):

        async def index(
            user: Annotated[Caller, Depends(current_user)],
            engine: Annotated[AsyncEngine, Depends(get_engine)],
            page: Annotated[int, Query(ge=1)] = 1,
            name: Annotated[str | None, Query(max_length=200)] = None,
        ) -> Any:
            return await _read(engine, user, kind, lambda reader: reader.index(kind, page, name))

        router.add_api_route(
            f"/{segment}",
            index,
            methods=["GET"],
            response_model=v.IndexPage,
            name=f"{label}_index",
            summary=f"The index of {segment}, by name",
        )


for _kind in SEGMENTS:
    _register(_kind)
