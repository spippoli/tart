import { describe, expect, it } from 'vitest';
import { fetchMapData, LOCATIONS_URL, mapDataOf } from './data';

const body = {
	type: 'FeatureCollection',
	features: [
		{
			type: 'Feature',
			geometry: { type: 'Point', coordinates: [12.5, 41.9] },
			properties: { id: 1, present: 1, unknown: 0, disappeared: 0, point: [12.5, 41.9] }
		}
	],
	sites: [{ id: 5, name: 'Deposito', path: '5-deposito', point: [12.5, 41.9] }],
	areas: [{ name: 'Quartiere', point: [12.5, 41.9] }]
};

describe('the Locations of the Discovery query', () => {
	it('become what the map draws, with the Site paths of the UI language', () => {
		const data = mapDataOf(body as never, (segment) => `/it/luoghi/${segment}`);
		expect(data.locations).toHaveLength(1);
		expect(data.sites[0].path).toBe('/it/luoghi/5-deposito');
		expect(data.areas).toEqual(body.areas);
	});

	it('are fetched with the filters of the query', async () => {
		const asked: string[] = [];
		const fetcher = (async (url: string) => {
			asked.push(url);
			return new Response(JSON.stringify(body));
		}) as unknown as typeof fetch;
		const result = await fetchMapData('type=stencil', String, fetcher);
		expect(asked).toEqual([`${LOCATIONS_URL}?type=stencil`]);
		expect('data' in result && result.data.locations).toHaveLength(1);
	});

	it('fail on an error status or a network error', async () => {
		const status = (async () => new Response('{}', { status: 500 })) as unknown as typeof fetch;
		const network = (async () => {
			throw new TypeError('offline');
		}) as unknown as typeof fetch;
		expect(await fetchMapData('', String, status)).toEqual({ failed: true });
		expect(await fetchMapData('', String, network)).toEqual({ failed: true });
	});
});
