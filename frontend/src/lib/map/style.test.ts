import { describe, expect, it } from 'vitest';
import { fetchStyle, styleUrl } from './style';

const TOKENS = {
	'map.paper': '#F3EEE2',
	'map.ink': '#2A2521',
	'marker.ink': '#1F1B18',
	'map.label.district': '#5E4636',
	'marker.accent': '#7A2E1C'
};
const STYLE = {
	version: 8,
	sources: {},
	layers: [],
	metadata: { 'tart:tokens': TOKENS, 'tart:insert-archive-below': 'labels' }
};

function answering(status: number, body: unknown): typeof fetch {
	return async (input) => {
		expect(input).toBe('/api/map/style/dark.json');
		return new Response(JSON.stringify(body), { status });
	};
}

describe('the served style of a theme', () => {
	it('is fetched from the style endpoint of the UI theme', async () => {
		expect(styleUrl('light')).toBe('/api/map/style/light.json');
		expect(await fetchStyle('dark', answering(200, STYLE))).toEqual({ style: STYLE });
	});

	// Discovery criterion 70: with no extract, the endpoint answers 503 tiles_missing.
	it('reports a missing tile extract', async () => {
		expect(await fetchStyle('dark', answering(503, { code: 'tiles_missing' }))).toEqual({
			unavailable: 'tiles_missing'
		});
	});

	it('reports any other failure as a style that fails to load', async () => {
		for (const fetcher of [
			answering(503, { detail: 'down' }),
			answering(500, STYLE),
			answering(200, { version: 8, layers: [] }),
			(async () => new Response('<html>', { status: 200 })) as typeof fetch,
			(async () => {
				throw new TypeError('offline');
			}) as typeof fetch
		]) {
			expect(await fetchStyle('dark', fetcher)).toEqual({ unavailable: 'style' });
		}
	});
});
