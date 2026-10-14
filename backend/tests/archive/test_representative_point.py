"""The Location's representative point (Discovery spec, The map), criterion 60."""

import asyncio

from sqlalchemy import text

from tart.db import create_engine


def _query(url: str, sql: str, **values: object) -> list[tuple[object, ...]]:
    async def run() -> list[tuple[object, ...]]:
        engine = create_engine(url)
        try:
            async with engine.begin() as connection:
                result = await connection.execute(text(sql), values)
                return [tuple(row) for row in result] if result.returns_rows else []
        finally:
            await engine.dispose()

    return asyncio.run(run())


def _insert(url: str, record_id: int, wkt: str) -> None:
    _query(
        url,
        "INSERT INTO record (id, kind) VALUES (:id, 'location')",
        id=record_id,
    )
    _query(
        url,
        "INSERT INTO location (id, geometry, approximate, surface_type) "
        "VALUES (:id, ST_GeomFromText(:wkt, 4326), false, 'wall')",
        id=record_id,
        wkt=wkt,
    )


def _point(url: str, record_id: int) -> tuple[float, float]:
    [(x, y)] = _query(
        url,
        "SELECT ST_X(representative_point), ST_Y(representative_point) "
        "FROM location WHERE id = :id",
        id=record_id,
    )
    return float(x), float(y)  # type: ignore[arg-type]


def test_a_point_is_its_own_representative_point(migrated_database: str) -> None:
    _insert(migrated_database, 1, "POINT(12.5 41.9)")
    assert _point(migrated_database, 1) == (12.5, 41.9)


def test_a_line_is_represented_by_the_point_at_half_its_length(migrated_database: str) -> None:
    _insert(migrated_database, 2, "LINESTRING(12.5 41.9, 12.52 41.9)")
    x, y = _point(migrated_database, 2)
    assert (round(x, 6), y) == (12.51, 41.9)


def test_a_bent_line_is_represented_by_a_point_on_it(migrated_database: str) -> None:
    _insert(migrated_database, 3, "LINESTRING(12.5 41.9, 12.5 41.91, 12.52 41.91)")
    [(on_line,)] = _query(
        migrated_database,
        "SELECT ST_DWithin(geometry, representative_point, 1e-9) FROM location WHERE id = 3",
    )
    assert on_line


def test_a_u_shaped_polygon_is_represented_by_a_point_inside_it(migrated_database: str) -> None:
    # The centroid of a U lies in its notch, outside the polygon.
    _insert(
        migrated_database,
        4,
        "POLYGON((12.5 41.9, 12.5 41.93, 12.51 41.93, 12.51 41.91, 12.52 41.91, "
        "12.52 41.93, 12.53 41.93, 12.53 41.9, 12.5 41.9))",
    )
    [(inside, centroid_outside)] = _query(
        migrated_database,
        "SELECT ST_Covers(geometry, representative_point), "
        "NOT ST_Covers(geometry, ST_Centroid(geometry)) FROM location WHERE id = 4",
    )
    assert inside
    assert centroid_outside


def test_editing_a_geometry_updates_its_representative_point(migrated_database: str) -> None:
    _insert(migrated_database, 5, "POINT(12.5 41.9)")
    _query(
        migrated_database,
        "UPDATE location SET geometry = ST_GeomFromText('POINT(12.6 42.0)', 4326) WHERE id = 5",
    )
    assert _point(migrated_database, 5) == (12.6, 42.0)
