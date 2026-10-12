import type { Bounds } from '#lib/map/bounds.ts';
import type { PageServerLoad } from './$types';

// The homepage of a UI language is its bare prefix with a slash: `/it/`, `/en/`.
export const trailingSlash = 'always';

/** What the Explore map needs from the public configuration. */
export const load: PageServerLoad = ({ locals }) => {
	const { geography, map_attribution } = locals.config;
	return {
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
