"""`/api/contribution/duplicates`: the candidates the editor shows before a duplicate is made
(contribution-and-moderation spec, Duplicate detection). Signed-in Users only.

    POST /api/contribution/duplicates/locations   Locations within 25 m of a geometry
    POST /api/contribution/duplicates/names       records whose name or Alias is alike
    POST /api/contribution/duplicates/area        what a drawn Area covers and overlaps

Neither endpoint ever blocks anything: they answer with candidates, possibly none, and the
editor lets the contributor go on. The requests are read-only; they are POSTs because a
geometry does not belong in a URL.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncEngine

from tart.api.auth import Error, current_user, get_engine
from tart.archive import Kind
from tart.archive.errors import ArchiveRuleViolation
from tart.archive.geometry import Geometry
from tart.archive_read import Reader, Viewer
from tart.archive_read import views as v
from tart.auth.sessions import SessionUser
from tart.moderation.duplicates import Match, name_candidates
from tart.moderation_persistence.duplicates import PostgresDuplicateQuery

router = APIRouter(prefix="/api/contribution/duplicates")

SIGN_IN_REQUIRED = "sign_in_required"
RECORD_NOT_FOUND = "record_not_found"
GEOMETRY_INVALID = "geometry_invalid"

_ERRORS: dict[int | str, dict] = {401: {"model": Error}, 404: {"model": Error}}

type Caller = Annotated[SessionUser | None, Depends(current_user)]
type Engine = Annotated[AsyncEngine, Depends(get_engine)]


class LocationQuery(BaseModel):
    """Either a geometry just placed, or an existing Location that was chosen."""

    geometry: dict | None = None
    """A GeoJSON Point, LineString, or Polygon."""
    uncertainty_radius: Annotated[int, Field(ge=1)] | None = None
    """In metres, for an approximate point."""
    location_id: int | None = None
    """An existing Location: its own geometry and radius are used."""

    @model_validator(mode="after")
    def _one_place(self) -> LocationQuery:
        if (self.geometry is None) == (self.location_id is None):
            raise ValueError("give either a geometry or a location_id")
        return self


class LocationCandidate(BaseModel):
    """A Location within the proximity rule, with all its Artworks, disappeared ones too."""

    location: v.LocationSummary
    distance: float
    """Metres between the geometries; ordered nearest first."""
    site: v.RecordLink | None
    artworks: list[v.ListEntry]
    """Each carries its Condition group, the sign the warning draws."""


class LocationCandidates(BaseModel):
    candidates: list[LocationCandidate]


class NameQuery(BaseModel):
    kind: Literal["artist", "site", "series", "area", "source"]
    name: Annotated[str, Field(min_length=1, max_length=200)]
    url: Annotated[str, Field(max_length=2000)] | None = None
    """A Source's URL, compared by its normalised form."""


class NameCandidate(BaseModel):
    record: v.RecordLink
    match: Match
    matched: str
    """The name, Alias, or URL that matched."""
    score: float


class NameCandidates(BaseModel):
    candidates: list[NameCandidate]


@router.post("/locations", response_model=LocationCandidates, responses=_ERRORS)
async def location_candidates(
    query: LocationQuery, user: Caller, engine: Engine
) -> LocationCandidates | JSONResponse:
    if user is None:
        return JSONResponse({"code": SIGN_IN_REQUIRED}, status_code=401)
    async with engine.connect() as connection:
        reader = Reader(connection, Viewer(moderator=False))
        radius = query.uncertainty_radius
        if query.location_id is not None:
            if not await reader.listed([query.location_id]):
                return JSONResponse({"code": RECORD_NOT_FOUND}, status_code=404)
            chosen = (await reader.shown(query.location_id)).record
            if chosen.geometry is None:  # redacted: there is nothing to compare
                return LocationCandidates(candidates=[])
            geometry, radius = chosen.geometry, chosen.uncertainty_radius
        else:
            try:
                geometry = Geometry.from_geojson(query.geometry or {})
            except ArchiveRuleViolation:
                return JSONResponse({"code": GEOMETRY_INVALID}, status_code=422)
        candidates = []
        for near in await PostgresDuplicateQuery(connection).locations_near(geometry, radius):
            if not await reader.listed([near.id]):
                continue
            if (await reader.shown(near.id)).record.geometry is None:
                continue  # redacted: its place is not public
            where = await reader.where(near.id, nearby=False)
            assert where.location is not None
            artworks = await reader.stratigraphy_of(near.id)
            candidates.append(
                LocationCandidate(
                    location=where.location,
                    distance=near.distance,
                    site=where.site,
                    artworks=await reader.entries(artworks),
                )
            )
        return LocationCandidates(candidates=candidates)


class AreaQuery(BaseModel):
    geometry: dict
    """A GeoJSON Polygon, as drawn."""


class AreaReadout(BaseModel):
    """What a drawn Area covers, for the text readout of the Polygon step."""

    locations: int
    """The public Locations that fall within it."""
    overlapping: list[v.RecordLink]
    """The existing Areas it overlaps; overlaps are allowed."""


@router.post("/area", response_model=AreaReadout, responses={401: {"model": Error}})
async def area_readout(
    query: AreaQuery, user: Caller, engine: Engine
) -> AreaReadout | JSONResponse:
    """How many Locations a polygon would contain and which Areas it overlaps. Read-only."""
    if user is None:
        return JSONResponse({"code": SIGN_IN_REQUIRED}, status_code=401)
    try:
        area = Geometry.from_geojson(query.geometry)
    except ArchiveRuleViolation:
        return JSONResponse({"code": GEOMETRY_INVALID}, status_code=422)
    async with engine.connect() as connection:
        reader = Reader(connection, Viewer(moderator=False))
        count, overlapping = await PostgresDuplicateQuery(connection).within_area(area)
        return AreaReadout(locations=count, overlapping=await reader.links(overlapping))


@router.post("/names", response_model=NameCandidates, responses={401: {"model": Error}})
async def name_candidates_for(
    query: NameQuery, user: Caller, engine: Engine
) -> NameCandidates | JSONResponse:
    if user is None:
        return JSONResponse({"code": SIGN_IN_REQUIRED}, status_code=401)
    kind = Kind(query.kind)
    async with engine.connect() as connection:
        reader = Reader(connection, Viewer(moderator=False))
        records = await PostgresDuplicateQuery(connection).named_records(kind)
        found = []
        for candidate in name_candidates(
            query.name, records, url=query.url if kind is Kind.SOURCE else None
        ):
            shown = (await reader.shown(candidate.record.id)).record
            # A Redaction hides the name or the Alias from the public, and so from the warning.
            if candidate.match is Match.NAME and not (
                getattr(shown, "name", None) or getattr(shown, "title", None)
            ):
                continue
            if candidate.match is Match.ALIAS and candidate.matched not in shown.aliases:
                continue
            if candidate.match is Match.URL and not getattr(shown, "url", None):
                continue
            [link] = await reader.links([candidate.record.id])
            found.append(
                NameCandidate(
                    record=link,
                    match=candidate.match,
                    matched=candidate.matched,
                    score=candidate.score,
                )
            )
        return NameCandidates(candidates=found)
