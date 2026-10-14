/**
 * The arithmetic of the Explore view (Discovery spec, Map/list sync and Filters and
 * the Explore viewport): what the viewport sends to the list and writes to the URL,
 * where the map fits, and the sign of a selection outside the filters.
 */
import type { Bounds } from '#lib/map/bounds.ts';
import type { View } from '#lib/map/engine.ts';
import type { LocationFeature, MapData } from '#lib/map/locations.ts';
import { extentOf, locationFeature, type Counts } from '#lib/map/record-maps.ts';
import type { components } from '../api/schema';
import type { Viewport } from './state';

type Entry = components['schemas']['ListEntry'];

/**
 * The Explore list while a map restricts it to the viewport (Discovery spec, Map/list
 * sync). Without it the list is the server-rendered page of every matching Artwork.
 */
export interface ViewportListing {
	/** The page of the viewport's Artworks; `null` while the first request is out. */
	results: components['schemas']['ArtworkPage'] | null;
	/** The request failed: no list, no signs, a "Retry". */
	failed: boolean;
	busy: boolean;
	/** Busy for more than 300 ms: "Updating results…". */
	updating: boolean;
	/** The selected Location, whose entries are labelled. */
	selected: number | null;
	onpage: (page: number) => void;
	onretry: () => void;
	onwiden: () => void;
	onshow: (entry: Entry) => void;
}

/** A fit to a single Location, or to a small place, stops here (platform constant). */
export const FIT_MAX_ZOOM = 17;

/** "Centre on my position" zooms here (platform constant). */
export const POSITION_ZOOM = 16;

/** The viewport the URL holds: a hundredth of a zoom level and about a metre are enough. */
export function viewportOf(zoom: number, [lon, lat]: readonly [number, number]): Viewport {
	return { zoom: round(zoom, 2), lat: round(lat, 5), lon: round(lon, 5) };
}

function round(value: number, decimals: number): number {
	return Number(value.toFixed(decimals));
}

export function viewOf({ zoom, lat, lon }: Viewport): View {
	return { center: [lon, lat], zoom };
}

/** The API's `bbox`: west, south, east, north. */
export function bboxParam([west, south, east, north]: Bounds): string {
	return [west, south, east, north].map((value) => round(value, 6)).join(',');
}

export function contains(
	[west, south, east, north]: Bounds,
	[lon, lat]: readonly [number, number]
): boolean {
	return lon >= west && lon <= east && lat >= south && lat <= north;
}

/**
 * Whether `point` lies in the middle of the view, away from its edges (and from what the
 * panel or the controls may cover): "Show on map" centres a Location that does not.
 */
export function central(bounds: Bounds, point: readonly [number, number]): boolean {
	const [west, south, east, north] = bounds;
	const [x, y] = [(east - west) * 0.2, (north - south) * 0.2];
	return contains([west + x, south + y, east - x, north - y], point);
}

/** The extent of the signs, `null` if there are none. */
export function extentOfSigns(locations: readonly LocationFeature[]): Bounds | null {
	return extentOf(
		locations.map(({ properties }) => ({ type: 'Point', coordinates: properties.point }))
	);
}

/** `extent` cut to the Instance boundary: a fit never leaves it; `null` if it lies outside. */
export function clampTo(extent: Bounds, boundary: Bounds): Bounds | null {
	const clamped: Bounds = [
		Math.max(extent[0], boundary[0]),
		Math.max(extent[1], boundary[1]),
		Math.min(extent[2], boundary[2]),
		Math.min(extent[3], boundary[3])
	];
	return clamped[0] <= clamped[2] && clamped[1] <= clamped[3] ? clamped : null;
}

/** The Locations of a panel's entries by Condition group: the sign drawn for a selection. */
export function countsOf(entries: readonly { condition: { group: keyof Counts } }[]): Counts {
	const counts: Counts = { present: 0, unknown: 0, disappeared: 0 };
	for (const { condition } of entries) counts[condition.group]++;
	return counts;
}

interface Selected {
	id: number;
	geometry: { [key: string]: unknown } | null;
	point?: [number, number] | null;
	approximate: boolean;
	uncertainty_radius?: number | null;
}

/**
 * The map's data with the selected Location in it: a public Location with no Artwork
 * matching the filters is selected anyway and its sign is drawn for the selection only.
 */
export function withSelection(data: MapData, selected: Selected | null, counts: Counts): MapData {
	if (!selected || data.locations.some(({ properties }) => properties.id === selected.id)) {
		return data;
	}
	const feature = locationFeature(selected, counts);
	return feature ? { ...data, locations: [...data.locations, feature] } : data;
}

/** Follows a link to a region of the page and puts the focus there, as skip links must. */
export function jump(event: MouseEvent, id: string) {
	event.preventDefault();
	const target = document.getElementById(id);
	target?.focus();
	target?.scrollIntoView();
}
