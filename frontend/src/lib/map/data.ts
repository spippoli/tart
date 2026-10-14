import { EMPTY_MAP_DATA, type MapData } from './locations';

/**
 * Where the Discovery query serves the lightweight response of all matching
 * Locations (Discovery spec, The map: Data), with an ETag for repeat requests.
 */
export const LOCATIONS_URL = '/api/map/locations';

/** Fetches the Locations, Sites, and Areas to draw; none if the request fails. */
export async function fetchMapData(fetcher: typeof fetch = fetch): Promise<MapData> {
	try {
		const response = await fetcher(LOCATIONS_URL, { headers: { accept: 'application/json' } });
		if (!response.ok) return EMPTY_MAP_DATA;
		const body = (await response.json()) as Partial<MapData>;
		return {
			locations: body.locations ?? [],
			sites: body.sites ?? [],
			areas: body.areas ?? []
		};
	} catch {
		return EMPTY_MAP_DATA;
	}
}
