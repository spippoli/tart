import type { Group } from './signs';

/**
 * What the map draws (Discovery spec, The map: signs, stack, clusters, geometries):
 * one feature per Location with at least one matching Artwork, carrying the counts of
 * those Artworks per Condition group and its representative point, plus the labels of
 * Sites and Areas. The geometry of a point is the point itself; a line or polygon
 * keeps its geometry for z17 and above.
 */
export type Position = [number, number];

export type LocationGeometry =
	| { type: 'Point'; coordinates: Position }
	| { type: 'LineString'; coordinates: Position[] }
	| { type: 'Polygon'; coordinates: Position[][] };

export interface LocationProperties {
	id: number;
	/** The matching Artworks of the Location, by Condition group. */
	present: number;
	unknown: number;
	disappeared: number;
	/** The representative point, where the sign sits (longitude, latitude). */
	point: Position;
	approximate: boolean;
	/** The uncertainty radius of an approximate point, in metres. */
	radius: number | null;
}

export interface LocationFeature {
	type: 'Feature';
	geometry: LocationGeometry;
	properties: LocationProperties;
}

export interface SiteLabel {
	id: number;
	name: string;
	/** The path of the Site page, with its language prefix. */
	path: string;
	/** The centroid of its Locations' representative points. */
	point: Position;
}

export interface AreaLabel {
	name: string;
	point: Position;
}

export interface MapData {
	locations: LocationFeature[];
	sites: SiteLabel[];
	areas: AreaLabel[];
}

export const EMPTY_MAP_DATA: MapData = { locations: [], sites: [], areas: [] };

export function artworkCount(properties: LocationProperties): number {
	return properties.present + properties.unknown + properties.disappeared;
}

/** *present* over *unknown* over *disappeared* (ADR 0015). */
export function prevailingGroup(properties: LocationProperties): Group {
	if (properties.present > 0) return 'present';
	if (properties.unknown > 0) return 'unknown';
	return 'disappeared';
}

/** The image a Location's sign is drawn with: its group, the stack, and the size. */
export function signImageName(properties: LocationProperties): string {
	const stack = artworkCount(properties) > 1 ? 'stack' : 'single';
	const size = properties.approximate ? 'small' : 'normal';
	return `sign-${prevailingGroup(properties)}-${stack}-${size}`;
}

interface PointFeature {
	type: 'Feature';
	geometry: { type: 'Point'; coordinates: Position };
	properties: Record<string, unknown>;
}

/** The signs: a point at the representative point of every Location. */
export function signFeatures(locations: readonly LocationFeature[]): PointFeature[] {
	return locations.map(({ properties }) => ({
		type: 'Feature',
		geometry: { type: 'Point', coordinates: properties.point },
		properties: {
			id: properties.id,
			count: artworkCount(properties),
			group: prevailingGroup(properties),
			image: signImageName(properties)
		}
	}));
}

/** The lines and polygons, which the map draws from z17, by prevailing group. */
export function geometryFeatures(locations: readonly LocationFeature[]) {
	return locations
		.filter(({ geometry }) => geometry.type !== 'Point')
		.map(({ geometry, properties }) => ({
			type: 'Feature' as const,
			geometry,
			properties: { id: properties.id, group: prevailingGroup(properties) }
		}));
}

const METRES_PER_DEGREE_LAT = 110_574;
const METRES_PER_DEGREE_LON_AT_EQUATOR = 111_320;
const CIRCLE_STEPS = 48;

/**
 * The hatched approximate area of every approximate point with an uncertainty radius
 * (ADR 0017): a circle of that radius. A point without a radius has none.
 */
export function hatchFeatures(locations: readonly LocationFeature[]) {
	const features = [];
	for (const { geometry, properties } of locations) {
		if (geometry.type !== 'Point' || !properties.approximate || !properties.radius) continue;
		const [longitude, latitude] = geometry.coordinates;
		const lat = properties.radius / METRES_PER_DEGREE_LAT;
		const lon =
			properties.radius / (METRES_PER_DEGREE_LON_AT_EQUATOR * Math.cos((latitude * Math.PI) / 180));
		const ring: Position[] = [];
		for (let step = 0; step < CIRCLE_STEPS; step++) {
			const angle = (2 * Math.PI * step) / CIRCLE_STEPS;
			ring.push([longitude + lon * Math.cos(angle), latitude + lat * Math.sin(angle)]);
		}
		ring.push(ring[0]);
		features.push({
			type: 'Feature' as const,
			geometry: { type: 'Polygon' as const, coordinates: [ring] },
			properties: { id: properties.id }
		});
	}
	return features;
}
