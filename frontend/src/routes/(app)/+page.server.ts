import type { Bounds } from '#lib/map/bounds.ts';
import { loadDiscovery } from '#lib/server/discovery.ts';
import type { PageServerLoad } from './$types';

// The homepage of a UI language is its bare prefix with a slash: `/it/`, `/en/`.
export const trailingSlash = 'always';

/** What the Explore map needs from the public configuration. */
export const load: PageServerLoad = async (event) => {
	const { geography, map_attribution } = event.locals.config;
	return {
		...(await loadDiscovery(event, 'explore')),
		map: {
			// The API's schema checks both lengths: a centre has two numbers, a box four.
			view: {
				center: geography.default_view.center as [number, number],
				zoom: geography.default_view.zoom
			},
			boundary: geography.bounds as unknown as Bounds,
			attribution: map_attribution
		}
	};
};
