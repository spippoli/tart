"""The Discovery query over PostgreSQL (Discovery spec, Modules): the Artworks that match a
search and filters, as a page of list entries, as the Locations of a map, with the records
that also match, and a Location's panel.

    discovery = Discovery(connection, content_language)
    page = await discovery.artworks(filters, page=1)

Only public, approved content is found: an Artwork is listed when neither it nor its
Location is withdrawn or merged, and the index holds the public facts of each (see
`tart.discovery.index`). No ordering reads views, clicks, or any engagement signal.
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import (
    ColumnElement,
    Select,
    and_,
    case,
    cast,
    desc,
    exists,
    func,
    literal,
    or_,
    select,
    true,
)
from sqlalchemy.dialects.postgresql import REGCONFIG, Range, distinct_on
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.orm import aliased

from tart.archive import Kind, RecordId, record_path_segment
from tart.archive_persistence import tables as archive
from tart.archive_read import (
    Reader,
    RecordMergedError,
    RecordNotFoundError,
    RecordWithdrawnError,
    Viewer,
)
from tart.discovery import tables as t
from tart.discovery import views as dv
from tart.discovery.filters import (
    PAGE_SIZE,
    Filters,
    Order,
    first_day,
    last_day,
)
from tart.discovery.language import text_search_configuration

NAME_THRESHOLD = 0.5
"""The least `word_similarity` of a name that matches (Search, Matching and relevance)."""
TEXT_RANK_WEIGHT = 0.5
ALSO_MATCHING_LIMIT = 3
ALSO_MATCHING_KINDS = (Kind.ARTIST, Kind.SERIES, Kind.SITE, Kind.AREA)

type BoundingBox = tuple[float, float, float, float]
"""West, south, east, north."""


class LocationNotAvailableError(Exception):
    """The Location is withdrawn, merged, or does not exist: one answer for all three."""


@dataclass(frozen=True)
class _Matching:
    """The Artworks that match, as a select with the columns `artwork`, `location`, `group`,
    and, with a search, `score`; and what to order them by."""

    select: Select[Any]
    order: list[ColumnElement[Any]]


def _listed(record: Any) -> ColumnElement[bool]:
    return and_(record.c.withdrawn_at.is_(None), record.c.merged_into.is_(None))


class Discovery:
    def __init__(self, connection: AsyncConnection, content_language: str) -> None:
        self.connection = connection
        self.content_language = content_language
        self.reader = Reader(connection, Viewer())

    # Matching.

    def _matching(
        self,
        filters: Filters,
        *,
        skip_creation: bool = False,
        box: BoundingBox | None = None,
    ) -> _Matching:
        d, a, location = t.discovery_artwork, archive.artwork, archive.location
        artwork_record, location_record = aliased(archive.record), aliased(archive.record)
        statement = select(
            a.c.id.label("artwork"),
            a.c.location_id.label("location"),
            d.c.condition_group.label("group"),
        ).select_from(
            d.join(a, a.c.id == d.c.artwork_id)
            .join(artwork_record, and_(artwork_record.c.id == a.c.id, _listed(artwork_record)))
            .join(location, location.c.id == a.c.location_id)
            .join(
                location_record,
                and_(location_record.c.id == location.c.id, _listed(location_record)),
            )
        )

        if filters.restricts_conditions:
            statement = statement.where(d.c.condition.in_([c.value for c in filters.conditions]))
        if filters.expression_types:
            statement = statement.where(
                a.c.expression_types.overlap(sorted(filters.expression_types))
            )
        if filters.areas:
            area, area_record = archive.area, aliased(archive.record)
            statement = statement.where(
                exists(
                    select(1)
                    .select_from(
                        area.join(
                            area_record, and_(area_record.c.id == area.c.id, _listed(area_record))
                        )
                    )
                    .where(
                        area.c.id.in_(sorted(filters.areas)),
                        func.ST_Intersects(area.c.geometry, location.c.geometry),
                    )
                )
            )
        if filters.attribution:
            statement = statement.where(
                d.c.attribution.overlap([x.value for x in filters.attribution])
            )
        if filters.artist is not None:
            artist_record = aliased(archive.record)
            statement = statement.where(
                exists(
                    select(1)
                    .select_from(
                        archive.attribution.join(
                            artist_record,
                            and_(
                                artist_record.c.id == archive.attribution.c.artist_id,
                                _listed(artist_record),
                            ),
                        )
                    )
                    .where(
                        archive.attribution.c.artwork_id == a.c.id,
                        archive.attribution.c.artist_id == filters.artist,
                    )
                )
            )
        if filters.series is not None:
            series_record = aliased(archive.record)
            statement = statement.where(
                exists(
                    select(1)
                    .select_from(
                        archive.artwork_series.join(
                            series_record,
                            and_(
                                series_record.c.id == archive.artwork_series.c.series_id,
                                _listed(series_record),
                            ),
                        )
                    )
                    .where(
                        archive.artwork_series.c.artwork_id == a.c.id,
                        archive.artwork_series.c.series_id == filters.series,
                    )
                )
            )
        if filters.documentation_dated:
            during = Range(
                first_day(filters.documented_from), last_day(filters.documented_to), bounds="[]"
            )
            statement = statement.where(
                exists(
                    select(1).where(
                        t.discovery_documented.c.artwork_id == a.c.id,
                        t.discovery_documented.c.during.overlaps(during),
                    )
                )
            )
        if filters.creation_dated and not skip_creation:
            during = Range(
                first_day(filters.created_from), last_day(filters.created_to), bounds="[]"
            )
            statement = statement.where(d.c.created_during.overlaps(during))
        if box is not None:
            statement = statement.where(
                func.ST_Intersects(
                    location.c.representative_point, func.ST_MakeEnvelope(*box, 4326)
                )
            )

        score: ColumnElement[Any] | None = None
        if (text := filters.query) is not None:
            statement, score = self._search(statement, text)
            statement = statement.add_columns(score.label("score"))
        return _Matching(statement, self._order(filters.effective_order, score))

    def _search(self, statement: Select[Any], text: str) -> tuple[Select[Any], ColumnElement[Any]]:
        """Restrict to the Artworks the text matches, and the score they are ranked by.

        A name matches by trigram similarity of its words, a description by full text with
        the Content language's stemming; the score is the best name similarity weighted by
        field plus half the description's rank, over 1.5 so that it lies between 0 and 1.
        """
        d, name = t.discovery_artwork, t.discovery_name
        folded = func.lower(func.unaccent(literal(text)))
        similarity = func.word_similarity(folded, name.c.name)
        names = (
            select(func.max(similarity * name.c.weight).label("best"))
            .where(name.c.artwork_id == d.c.artwork_id, similarity >= NAME_THRESHOLD)
            .lateral("names")
        )
        query = func.websearch_to_tsquery(
            cast(text_search_configuration(self.content_language), REGCONFIG), folded
        )
        in_description = d.c.description.bool_op("@@")(query)
        rank = case((in_description, func.ts_rank_cd(d.c.description, query, 32)), else_=0.0)
        score = (func.coalesce(names.c.best, 0.0) + TEXT_RANK_WEIGHT * rank) / (
            1 + TEXT_RANK_WEIGHT
        )
        return (
            statement.outerjoin(names, true()).where(
                or_(names.c.best.is_not(None), in_description)
            ),
            score,
        )

    @staticmethod
    def _order(order: Order, score: ColumnElement[Any] | None) -> list[ColumnElement[Any]]:
        d = t.discovery_artwork
        by_id = archive.artwork.c.id
        most_recent = desc(d.c.last_documented).nulls_last()
        match order:
            case Order.OLDEST:
                return [d.c.first_documented.asc().nulls_last(), by_id]
            case Order.ADDED:
                return [d.c.added_at.desc(), by_id]
            case Order.TITLE:
                # "Untitled" last; the rest alphabetical in the Content language.
                return [d.c.title.is_(None), d.c.title.collate("und-x-icu"), by_id]
            case Order.RELEVANCE if score is not None:
                return [desc(score), most_recent, by_id]
        return [most_recent, by_id]

    # The list.

    async def artworks(
        self, filters: Filters, page: int = 1, box: BoundingBox | None = None
    ) -> dv.ArtworkPage:
        """One page of the matching Artworks, with the total, the records that also match
        the search, and how many the "Created between" filter leaves out."""
        matching = self._matching(filters, box=box)
        total = await self.connection.scalar(
            select(func.count()).select_from(matching.select.subquery())
        )
        ids = await self.connection.scalars(
            matching.select.order_by(*matching.order)
            .limit(PAGE_SIZE)
            .offset((page - 1) * PAGE_SIZE)
        )
        return dv.ArtworkPage(
            entries=await self.reader.entries([row for row in ids]),
            total=total or 0,
            page=page,
            page_size=PAGE_SIZE,
            also_matching=await self.also_matching(filters.query) if filters.query else None,
            left_out=await self._left_out(filters, box),
        )

    async def _left_out(self, filters: Filters, box: BoundingBox | None) -> int:
        """The Artworks that match but for a creation date they do not have."""
        if not filters.creation_dated:
            return 0
        others = self._matching(filters, skip_creation=True, box=box).select
        undated = others.where(t.discovery_artwork.c.created_during.is_(None))
        return (
            await self.connection.scalar(select(func.count()).select_from(undated.subquery())) or 0
        )

    # The map.

    async def etag(self, filters: Filters) -> str:
        """From the counter of changes to the public archive and the normalised query."""
        counter = await self.connection.scalar(
            select(t.archive_change.c.counter).where(t.archive_change.c.id == 1)
        )
        digest = hashlib.sha256(f"{counter}|{filters.canonical()}".encode()).hexdigest()
        return f'"{digest[:32]}"'

    async def locations(self, filters: Filters) -> dict[str, Any]:
        """Every Location with a matching Artwork, as one lightweight GeoJSON collection:
        its geometry, representative point, and the matching Artworks per Condition group.

        Sites with a matching Location and every Area come as labels beside the features.
        """
        matching = self._matching(filters).select.subquery()
        location = archive.location
        rows = await self.connection.execute(
            select(
                location.c.id,
                func.count().filter(matching.c.group == "present").label("present"),
                func.count().filter(matching.c.group == "unknown").label("unknown"),
                func.count().filter(matching.c.group == "disappeared").label("disappeared"),
                func.ST_AsGeoJSON(location.c.geometry, 6).label("geometry"),
                func.ST_AsGeoJSON(location.c.representative_point, 6).label("point"),
                location.c.approximate,
                location.c.uncertainty_radius,
            )
            .select_from(matching.join(location, location.c.id == matching.c.location))
            .group_by(location.c.id)
            .order_by(location.c.id)
        )
        features = []
        for row in rows:
            total = row.present + row.unknown + row.disappeared
            group = "present" if row.present else "unknown" if row.unknown else "disappeared"
            features.append(
                {
                    "type": "Feature",
                    "geometry": json.loads(row.geometry),
                    "properties": {
                        "id": row.id,
                        "present": row.present,
                        "unknown": row.unknown,
                        "disappeared": row.disappeared,
                        "group": group,
                        "count": total,
                        "point": json.loads(row.point)["coordinates"],
                        "approximate": row.approximate,
                        "radius": row.uncertainty_radius,
                    },
                }
            )
        return {
            "type": "FeatureCollection",
            "features": features,
            "sites": await self._site_labels(matching),
            "areas": await self._area_labels(),
        }

    async def locations_json(self, filters: Filters) -> bytes:
        """The Locations collection as compact JSON."""
        return json.dumps(await self.locations(filters), separators=(",", ":")).encode()

    async def _site_labels(self, matching: Any) -> list[dict[str, Any]]:
        """A Site is labelled at the centroid of its matching Locations' representative points."""
        site, location, record = archive.site, archive.location, archive.record
        centroid = func.ST_Centroid(func.ST_Collect(location.c.representative_point))
        rows = await self.connection.execute(
            select(
                site.c.id,
                site.c.name,
                func.ST_X(centroid).label("x"),
                func.ST_Y(centroid).label("y"),
            )
            .select_from(
                matching.join(location, location.c.id == matching.c.location)
                .join(site, site.c.id == location.c.site_id)
                .join(record, and_(record.c.id == site.c.id, _listed(record)))
            )
            .group_by(site.c.id, site.c.name)
            .order_by(site.c.id)
        )
        return [
            {
                "id": row.id,
                "name": row.name,
                "path": record_path_segment(row.id, row.name),
                "point": [round(row.x, 6), round(row.y, 6)],
            }
            for row in rows
        ]

    async def _area_labels(self) -> list[dict[str, Any]]:
        area, record = archive.area, archive.record
        point = func.ST_PointOnSurface(area.c.geometry)
        rows = await self.connection.execute(
            select(area.c.name, func.ST_X(point).label("x"), func.ST_Y(point).label("y"))
            .select_from(area.join(record, and_(record.c.id == area.c.id, _listed(record))))
            .order_by(area.c.id)
        )
        return [{"name": row.name, "point": [round(row.x, 6), round(row.y, 6)]} for row in rows]

    # The Location panel.

    async def panel(self, location_id: RecordId, filters: Filters) -> dv.LocationPanel:
        """A Location's header and its stratigraphy of matching Artworks, and how many do not
        match. With none matching, the full stratigraphy, flagged, so that a shared link
        always works."""
        try:
            await self.reader.resolve(Kind.LOCATION, location_id)
        except (RecordNotFoundError, RecordWithdrawnError, RecordMergedError) as unavailable:
            raise LocationNotAvailableError(location_id) from unavailable
        where = await self.reader.where(location_id)
        assert where.location is not None
        stratigraphy = await self.reader.stratigraphy_of(location_id)
        matching = self._matching(filters).select.where(
            archive.artwork.c.location_id == location_id
        )
        found = set(await self.connection.scalars(select(matching.subquery().c.artwork)))
        shown = [id_ for id_ in stratigraphy if id_ in found]
        return dv.LocationPanel(
            location=where.location,
            site=where.site,
            areas=where.areas,
            entries=await self.reader.entries(shown or stratigraphy),
            matches=bool(shown),
            other=len(stratigraphy) - len(shown) if shown else 0,
        )

    # Also matching.

    async def also_matching(self, text: str) -> dv.AlsoMatching | None:
        """The Artists, Series, Sites, and Areas whose name or Alias matches, at most three of
        each, by similarity, then name in the Content language, then id."""
        folded = func.lower(func.unaccent(literal(text)))
        kinds = []
        for kind in ALSO_MATCHING_KINDS:
            matches = await self._records_named(kind, folded)
            if matches:
                kinds.append(
                    dv.AlsoMatchingKind(
                        kind=kind, items=matches[:ALSO_MATCHING_LIMIT], total=len(matches)
                    )
                )
        return dv.AlsoMatching(kinds=kinds) if kinds else None

    async def _records_named(self, kind: Kind, folded: ColumnElement[Any]) -> list[dv.AlsoMatch]:
        record = archive.record
        if kind is Kind.ARTIST:
            artist, alias = archive.artist, archive.artist_alias
            names = (
                select(
                    artist.c.id.label("id"),
                    artist.c.name.label("name"),
                    literal(None).label("alias"),
                )
                .union_all(
                    select(artist.c.id, artist.c.name, alias.c.name).join(
                        alias, alias.c.artist_id == artist.c.id
                    )
                )
                .subquery()
            )
            shown = func.coalesce(names.c.alias, names.c.name)
        else:
            table = {Kind.SERIES: archive.series, Kind.SITE: archive.site, Kind.AREA: archive.area}[
                kind
            ]
            names = select(
                table.c.id.label("id"), table.c.name.label("name"), literal(None).label("alias")
            ).subquery()
            shown = names.c.name
        similarity = func.word_similarity(folded, func.lower(func.unaccent(shown)))
        candidates = (
            select(
                names.c.id,
                names.c.name,
                names.c.alias,
                similarity.label("similarity"),
            )
            .select_from(names.join(record, and_(record.c.id == names.c.id, _listed(record))))
            .where(similarity >= NAME_THRESHOLD)
            # An Artist matched through both its name and an Alias counts once, by the best.
            .ext(distinct_on(names.c.id))
            .order_by(names.c.id, desc(similarity), names.c.alias.is_(None).desc())
            .subquery()
        )
        rows = await self.connection.execute(
            select(candidates).order_by(
                desc(candidates.c.similarity),
                candidates.c.name.collate("und-x-icu"),
                candidates.c.id,
            )
        )
        matches = []
        for row in rows:
            link = await self.reader.link((await self.reader.listed([row.id]))[0])
            if link.name is None:  # the name is redacted: the public cannot find it
                continue
            alias = row.alias if row.alias is not None and row.alias != row.name else None
            matches.append(dv.AlsoMatch(record=link, alias=alias))
        return matches
