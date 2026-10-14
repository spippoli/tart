import type { Bounds } from './bounds';
import type { LocationFeature, LocationGeometry, Position } from './locations';
import type { Group } from './signs';

/**
 * What the maps of the record pages are made from (Discovery spec, Mini-map; archive
 * records, Site, Area, and Series pages): the extent they frame, the Location they
 * highlight, and the link to Explore.
 */

/** A framed Location is shown at this zoom, or at its extent if that is larger. */
export const RECORD_MAP_ZOOM = 17;

interface Geometry {
	type: string;
	coordinates: unknown;
}

function positions(geometry: Geometry): Position[] {
	switch (geometry.type) {
		case 'Point':
			return [geometry.coordinates as Position];
		case 'LineString':
			return geometry.coordinates as Position[];
		case 'Polygon':
			return (geometry.coordinates as Position[][]).flat();
		default:
			return [];
	}
}

/** The bounding box of the geometries (west, south, east, north); `null` for none. */
export function extentOf(geometries: readonly Geometry[]): Bounds | null {
	const all = geometries.flatMap(positions);
	if (all.length === 0) return null;
	const longitudes = all.map(([longitude]) => longitude);
	const latitudes = all.map(([, latitude]) => latitude);
	return [
		Math.min(...longitudes),
		Math.min(...latitudes),
		Math.max(...longitudes),
		Math.max(...latitudes)
	];
}

export interface PlainLocation {
	id: number;
	geometry: { [key: string]: unknown } | null;
	point?: [number, number] | null;
	approximate: boolean;
	uncertainty_radius?: number | null;
}

export type Counts = Record<Group, number>;

/** A Location of a record page as the map module draws it; `null` if its geometry is redacted. */
export function locationFeature(
	location: PlainLocation,
	counts: Partial<Counts>
): LocationFeature | null {
	if (!location.geometry) return null;
	const geometry = location.geometry as unknown as LocationGeometry;
	const point = location.point ?? positions(geometry)[0];
	if (!point) return null;
	return {
		type: 'Feature',
		geometry,
		properties: {
			id: location.id,
			present: counts.present ?? 0,
			unknown: counts.unknown ?? 0,
			disappeared: counts.disappeared ?? 0,
			point,
			approximate: location.approximate,
			radius: location.uncertainty_radius ?? null
		}
	};
}

/** The localized query-string keys of the selection and the viewport. */
export interface ExploreKeys {
	selection: string;
	viewport: string;
}

/**
 * The link to Explore with the Location selected and the map on it, `?superficie=…&mappa=…`
 * with the viewport as `<z>/<lat>/<lon>`.
 */
export function exploreHref(
	explore: string,
	keys: ExploreKeys,
	id: number,
	[longitude, latitude]: Position,
	zoom = RECORD_MAP_ZOOM
): string {
	const viewport = `${zoom}/${latitude.toFixed(5)}/${longitude.toFixed(5)}`;
	return `${explore}?${keys.selection}=${id}&${keys.viewport}=${viewport}`;
}
