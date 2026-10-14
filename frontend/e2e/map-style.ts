import type { Page, Route } from '@playwright/test';
import { readFileSync } from 'node:fs';

/**
 * Fictional served styles for the map tests: a paper background, an inline GeoJSON
 * source (which MapLibre's worker parses), and one layer to insert the archive
 * layers below, with no glyphs or tiles, so nothing leaves the browser. The two
 * themes differ in every token.
 */
export const TOKENS = {
	light: {
		'map.paper': '#f3eee2',
		'map.ink': '#2a2521',
		'marker.ink': '#1f1b18',
		'map.label.district': '#5e4636',
		'marker.accent': '#7a2e1c'
	},
	dark: {
		'map.paper': '#1b1916',
		'map.ink': '#e6dfd2',
		'marker.ink': '#f3eee2',
		'map.label.district': '#cdb8a8',
		'marker.accent': '#f0a08c'
	}
};

export function style(theme: 'light' | 'dark') {
	const paper = TOKENS[theme]['map.paper'];
	return {
		version: 8,
		sources: {
			overlay: {
				type: 'geojson',
				data: {
					type: 'Feature',
					properties: {},
					geometry: { type: 'Point', coordinates: [12.4823, 41.8955] }
				}
			}
		},
		layers: [
			{ id: 'background', type: 'background', paint: { 'background-color': paper } },
			{
				id: 'overlay',
				type: 'circle',
				source: 'overlay',
				paint: { 'circle-color': TOKENS[theme]['map.ink'] }
			},
			{ id: 'labels', type: 'background', paint: { 'background-opacity': 0 } }
		],
		metadata: { 'tart:tokens': TOKENS[theme], 'tart:insert-archive-below': 'labels' }
	};
}

/** Answers the style endpoint as the API would, or with `failure` for both themes. */
export async function serveStyles(
	page: Page,
	failure?: { status: number; body: unknown }
): Promise<void> {
	await page.route('**/api/map/style/*.json', (route: Route) => {
		const theme = route.request().url().endsWith('/dark.json') ? 'dark' : 'light';
		return route.fulfill({
			status: failure?.status ?? 200,
			contentType: 'application/json',
			body: JSON.stringify(failure?.body ?? style(theme))
		});
	});
}

/** Answers the Locations request as the Discovery query would, over the fictional Locations. */
export async function serveLocations(page: Page): Promise<void> {
	const body = readFileSync(new URL('fixtures/map/locations.json', import.meta.url), 'utf8');
	await page.route('**/api/map/locations', (route: Route) =>
		route.fulfill({ status: 200, contentType: 'application/json', body })
	);
}
