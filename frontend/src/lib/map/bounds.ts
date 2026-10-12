/** West, south, east, north, in degrees. */
export type Bounds = readonly [number, number, number, number];

/** The tile extract covers the boundary buffered by this distance (platform constant). */
export const BUFFER_METRES = 2000;

/** No map zooms in beyond this (platform constant). */
export const MAX_ZOOM = 19;

// The same local projection as the tile pipeline's buffer (backend `tart.tiles`).
const METRES_PER_DEGREE_LAT = 110_574;
const METRES_PER_DEGREE_LON_AT_EQUATOR = 111_320;

/**
 * The bounds every map keeps to (Discovery spec, Map bounds and zoom): the bounding
 * box of the Instance boundary, `boundary`, buffered by 2 km, which is the area of
 * the tile extract. The longitude buffer is taken at the latitude farthest from
 * the equator, where a degree is shortest, so the box never falls short of it.
 */
export function mapBounds(boundary: Bounds): Bounds {
	const [west, south, east, north] = boundary;
	const latitude = Math.max(Math.abs(south), Math.abs(north));
	const lat = BUFFER_METRES / METRES_PER_DEGREE_LAT;
	const lon =
		BUFFER_METRES / (METRES_PER_DEGREE_LON_AT_EQUATOR * Math.cos((latitude * Math.PI) / 180));
	return [west - lon, Math.max(south - lat, -85), east + lon, Math.min(north + lat, 85)];
}
