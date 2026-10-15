import type { Bounds } from '#lib/map/bounds.ts';

/** What a map needs from the public configuration: Explore's and the record pages'. */
export function mapSettings({ config }: App.Locals) {
	const { geography, map_attribution } = config;
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
}
