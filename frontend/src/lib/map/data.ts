import { type LocationFeature, type MapData, type SiteLabel } from './locations';

/**
 * Where the Discovery query serves the lightweight response of all matching
 * Locations (Discovery spec, The map: Data), with an ETag for repeat requests: the
 * browser revalidates it, so a repeat costs a 304.
 */
export const LOCATIONS_URL = '/api/discovery/locations';

/** What the Locations request came to: the data, or a failure the page says in words. */
export type MapResult = { data: MapData } | { failed: true };

interface Body {
	features?: LocationFeature[];
	sites?: SiteLabel[];
	areas?: MapData['areas'];
}

/**
 * The data the map draws from the response. The API sends a Site by its `{id}-{slug}`
 * segment; `sitePath` makes it the path of its page.
 */
export function mapDataOf(body: Body, sitePath: (segment: string) => string): MapData {
	return {
		locations: body.features ?? [],
		sites: (body.sites ?? []).map((site) => ({ ...site, path: sitePath(site.path) })),
		areas: body.areas ?? []
	};
}

/**
 * Fetches the Locations that match `query` (the filters in the API's own parameters,
 * from `apiQuery`), their Sites, and the Areas to label.
 */
export async function fetchMapData(
	query: string,
	sitePath: (segment: string) => string,
	fetcher: typeof fetch = fetch,
	signal?: AbortSignal
): Promise<MapResult> {
	try {
		const response = await fetcher(`${LOCATIONS_URL}?${query}`, {
			headers: { accept: 'application/json' },
			signal
		});
		if (!response.ok) return { failed: true };
		return { data: mapDataOf((await response.json()) as Body, sitePath) };
	} catch {
		return { failed: true };
	}
}
