"""The PostgreSQL adapter of duplicate detection: PostGIS distances for the proximity rule,
the archive's tables for the name rule, and the queue's flag for pending creates.

It works on one `AsyncConnection`. Only public records are candidates: a withdrawn or merged
record is never offered.
"""

import json

from geoalchemy2 import Geography
from sqlalchemy import and_, cast, func, literal, select, text
from sqlalchemy.ext.asyncio import AsyncConnection

from tart.archive.changeset import Create
from tart.archive.geometry import Geometry
from tart.archive.records import Kind, Location
from tart.archive_persistence import tables as t
from tart.moderation import decode_content
from tart.moderation.duplicates import (
    PROXIMITY_METRES,
    NamedRecord,
    NearLocation,
)
from tart.moderation.model import Status
from tart.moderation_persistence import tables as s


def _geography(geometry: Geometry) -> object:
    return cast(
        func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(geometry.to_geojson())), 4326),
        Geography,
    )


_PUBLIC = (t.record.c.withdrawn_at.is_(None), t.record.c.merged_into.is_(None))


class PostgresDuplicateQuery:
    """`tart.moderation.duplicates.DuplicateQuery` over the archive's tables."""

    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def locations_near(self, geometry: Geometry, radius: int | None) -> list[NearLocation]:
        here = _geography(geometry)
        there = cast(t.location.c.geometry, Geography)
        distance = func.ST_Distance(there, here)
        limit = PROXIMITY_METRES + func.coalesce(t.location.c.uncertainty_radius, 0) + (radius or 0)
        rows = await self.connection.execute(
            select(t.location.c.id, distance.label("distance"))
            .join(t.record, t.record.c.id == t.location.c.id)
            .where(*_PUBLIC, distance <= limit)
            .order_by(distance, t.location.c.id)
        )
        return [NearLocation(row.id, row.distance) for row in rows]

    async def within_area(self, area: Geometry) -> tuple[int, list[int]]:
        """What a proposed Area would cover: the public Locations that fall within it, and the
        ids of the public Areas it overlaps (overlaps are allowed)."""
        shape = func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(area.to_geojson())), 4326)
        locations = await self.connection.scalar(
            select(func.count())
            .select_from(t.location)
            .join(t.record, t.record.c.id == t.location.c.id)
            .where(*_PUBLIC, func.ST_Intersects(shape, t.location.c.geometry))
        )
        areas = await self.connection.scalars(
            select(t.area.c.id)
            .join(t.record, t.record.c.id == t.area.c.id)
            .where(*_PUBLIC, func.ST_Intersects(shape, t.area.c.geometry))
            .order_by(t.area.c.id)
        )
        return locations or 0, list(areas)

    async def named_records(self, kind: Kind) -> list[NamedRecord]:
        table = {
            Kind.ARTIST: t.artist,
            Kind.SITE: t.site,
            Kind.SERIES: t.series,
            Kind.AREA: t.area,
            Kind.SOURCE: t.source,
        }[kind]
        name = table.c.title if kind is Kind.SOURCE else table.c.name
        url = t.source.c.url if kind is Kind.SOURCE else literal(None)
        rows = await self.connection.execute(
            select(table.c.id, name.label("name"), url.label("url"))
            .join(t.record, t.record.c.id == table.c.id)
            .where(*_PUBLIC)
            .order_by(table.c.id)
        )
        aliases: dict[int, list[str]] = {}
        if kind is Kind.ARTIST:
            for row in await self.connection.execute(
                select(t.artist_alias.c.artist_id, t.artist_alias.c.name).order_by(
                    t.artist_alias.c.artist_id, t.artist_alias.c.position
                )
            ):
                aliases.setdefault(row.artist_id, []).append(row.name)
        return [
            NamedRecord(row.id, kind, row.name, tuple(aliases.get(row.id, ())), row.url)
            for row in rows
        ]


_PENDING_PROXIMITY = text(
    """
    SELECT a.submission_id AS first, b.submission_id AS second
    FROM jsonb_to_recordset(CAST(:places AS jsonb))
         AS a(submission_id bigint, geometry text, radius int)
    JOIN jsonb_to_recordset(CAST(:places AS jsonb))
         AS b(submission_id bigint, geometry text, radius int)
      ON a.submission_id < b.submission_id
     AND ST_Distance(
            CAST(ST_SetSRID(ST_GeomFromGeoJSON(a.geometry), 4326) AS geography),
            CAST(ST_SetSRID(ST_GeomFromGeoJSON(b.geometry), 4326) AS geography)
         ) <= :metres + coalesce(a.radius, 0) + coalesce(b.radius, 0)
    """
)


async def nearby_pending_creates(connection: AsyncConnection) -> dict[int, tuple[int, ...]]:
    """For each Submission awaiting a decision that creates a Location, the other such
    Submissions whose new Location is within the proximity rule of its own: the queue's flag
    (contribution-and-moderation spec, Pending duplicates). Submissions without a pair are
    absent."""
    latest = s.submission_round.alias("latest")
    rows = await connection.execute(
        select(s.submission.c.id, s.submission.c.target_kind, s.submission_round.c.snapshot)
        .join(s.submission_round, s.submission_round.c.submission_id == s.submission.c.id)
        .where(
            and_(
                s.submission.c.status == Status.SUBMITTED.value,
                s.submission.c.target_id.is_(None),
                s.submission_round.c.number
                == select(func.max(latest.c.number))
                .where(latest.c.submission_id == s.submission.c.id)
                .scalar_subquery(),
            )
        )
    )
    places = []
    for row in rows:
        for operation in decode_content(row.snapshot, Kind(row.target_kind)).operations:
            if isinstance(operation, Create) and isinstance(operation.record, Location):
                location = operation.record
                places.append(
                    {
                        "submission_id": row.id,
                        "geometry": json.dumps(location.geometry.to_geojson()),
                        "radius": location.uncertainty_radius,
                    }
                )
    if len(places) < 2:
        return {}
    pairs = await connection.execute(
        _PENDING_PROXIMITY, {"places": json.dumps(places), "metres": PROXIMITY_METRES}
    )
    flagged: dict[int, set[int]] = {}
    for pair in pairs:
        flagged.setdefault(pair.first, set()).add(pair.second)
        flagged.setdefault(pair.second, set()).add(pair.first)
    return {submission: tuple(sorted(others)) for submission, others in sorted(flagged.items())}
