"""`/api/discovery`: search and filters over the public archive (Discovery spec).

    GET /api/discovery/artworks?q=&order=&...&page=N&bbox=   a page of list entries, with the total
    GET /api/discovery/locations?q=&order=&...               all matching Locations, one GeoJSON
    GET /api/discovery/locations/{id}?...                    a Location's panel

All three take the same filters: OR within a filter, AND across (repeat a parameter for
several values). The Locations answer carries an ETag, so a repeat costs a 304. The
frontend turns its localized query string into these parameters.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncEngine

from tart.api.auth import Error, get_configuration, get_engine
from tart.archive import Condition
from tart.config import Configuration
from tart.discovery import views as dv
from tart.discovery.filters import AttributionFilter, Filters, Order
from tart.discovery.query import BoundingBox, Discovery, LocationNotAvailableError

router = APIRouter(prefix="/api/discovery")

LOCATION_NOT_AVAILABLE = "location_not_available"
MAX_YEAR = 9999


def filters(
    q: Annotated[
        str | None, Query(description="Search text; under 2 characters is absent.")
    ] = None,
    order: Annotated[Order | None, Query()] = None,
    condition: Annotated[list[Condition], Query()] = [],  # noqa: B006
    expression_type: Annotated[list[str], Query(alias="type")] = [],  # noqa: B006
    area: Annotated[list[int], Query()] = [],  # noqa: B006
    attribution: Annotated[list[AttributionFilter], Query()] = [],  # noqa: B006
    artist: Annotated[int | None, Query()] = None,
    series: Annotated[int | None, Query()] = None,
    documented_from: Annotated[int | None, Query(ge=1, le=MAX_YEAR)] = None,
    documented_to: Annotated[int | None, Query(ge=1, le=MAX_YEAR)] = None,
    created_from: Annotated[int | None, Query(ge=1, le=MAX_YEAR)] = None,
    created_to: Annotated[int | None, Query(ge=1, le=MAX_YEAR)] = None,
) -> Filters:
    return Filters(
        q=q,
        order=order,
        conditions=frozenset(condition),
        expression_types=frozenset(expression_type),
        areas=frozenset(area),
        attribution=frozenset(attribution),
        artist=artist,
        series=series,
        documented_from=documented_from,
        documented_to=documented_to,
        created_from=created_from,
        created_to=created_to,
    )


def bounding_box(
    bbox: Annotated[
        str | None,
        Query(description="West,south,east,north: only Locations whose sign lies inside."),
    ] = None,
) -> BoundingBox | None:
    if bbox is None:
        return None
    try:
        west, south, east, north = (float(part) for part in bbox.split(","))
    except ValueError:
        raise HTTPException(422, "bbox must be west,south,east,north") from None
    return west, south, east, north


Filter = Annotated[Filters, Depends(filters)]


@router.get("/artworks", response_model=dv.ArtworkPage)
async def artworks(
    selected: Filter,
    box: Annotated[BoundingBox | None, Depends(bounding_box)],
    configuration: Annotated[Configuration, Depends(get_configuration)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    page: Annotated[int, Query(ge=1)] = 1,
) -> Any:
    """The matching Artworks as list entries, 24 to a page, with the total."""
    async with engine.connect() as connection:
        discovery = Discovery(connection, configuration.instance.settings.languages.content)
        return await discovery.artworks(selected, page, box)


@router.get(
    "/locations",
    response_model=dv.MapLocations,
    responses={304: {"description": "The ETag sent is still current."}},
)
async def locations(
    request: Request,
    selected: Filter,
    configuration: Annotated[Configuration, Depends(get_configuration)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
) -> Response:
    """Every Location with a matching Artwork, as one lightweight GeoJSON collection.

    Revalidated on every use (`no-cache` with an ETag derived from the counter of public
    archive changes and the normalised query).
    """
    async with engine.connect() as connection:
        discovery = Discovery(connection, configuration.instance.settings.languages.content)
        etag = await discovery.etag(selected)
        headers = {"Cache-Control": "no-cache", "ETag": etag}
        sent = {
            tag.strip().removeprefix("W/")
            for tag in request.headers.get("If-None-Match", "").split(",")
        }
        if etag in sent or "*" in sent:
            return Response(status_code=304, headers=headers)
        body = await discovery.locations_json(selected)
    return Response(body, media_type="application/json", headers=headers)


@router.get(
    "/locations/{location_id}",
    response_model=dv.LocationPanel,
    responses={404: {"model": Error, "description": f"`{LOCATION_NOT_AVAILABLE}`"}},
)
async def location_panel(
    location_id: int,
    selected: Filter,
    configuration: Annotated[Configuration, Depends(get_configuration)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
) -> Any:
    """A Location's header and its stratigraphy of matching Artworks.

    A withdrawn, merged, or missing Location answers the same 404.
    """
    async with engine.connect() as connection:
        discovery = Discovery(connection, configuration.instance.settings.languages.content)
        try:
            return await discovery.panel(location_id, selected)
        except LocationNotAvailableError:
            return JSONResponse({"code": LOCATION_NOT_AVAILABLE}, status_code=404)
