import { describe, expect, it } from 'vitest';
import { exploreHref, extentOf, locationFeature, RECORD_MAP_ZOOM } from './record-maps';

describe('extentOf', () => {
	it('frames a point on itself, so that a fit stops at the maximum zoom', () => {
		expect(extentOf([{ type: 'Point', coordinates: [12.48, 41.89] }])).toEqual([
			12.48, 41.89, 12.48, 41.89
		]);
	});

	it('frames a line or a polygon on its whole extent', () => {
		expect(
			extentOf([
				{
					type: 'LineString',
					coordinates: [
						[12.47, 41.9],
						[12.4712, 41.9004]
					]
				}
			])
		).toEqual([12.47, 41.9, 12.4712, 41.9004]);
		expect(
			extentOf([
				{
					type: 'Polygon',
					coordinates: [
						[
							[12.47, 41.88],
							[12.5, 41.88],
							[12.5, 41.9],
							[12.47, 41.9],
							[12.47, 41.88]
						]
					]
				}
			])
		).toEqual([12.47, 41.88, 12.5, 41.9]);
	});

	it('takes the union of several geometries, and none for none', () => {
		expect(
			extentOf([
				{ type: 'Point', coordinates: [12.4, 41.8] },
				{ type: 'Point', coordinates: [12.6, 41.95] }
			])
		).toEqual([12.4, 41.8, 12.6, 41.95]);
		expect(extentOf([])).toBeNull();
	});
});

describe('locationFeature', () => {
	const point = { type: 'Point', coordinates: [12.48, 41.89] };

	it('carries the counts of its Artworks by Condition group', () => {
		const feature = locationFeature(
			{ id: 11, geometry: point, point: [12.48, 41.89], approximate: false },
			{ disappeared: 2 }
		);

		expect(feature?.properties).toMatchObject({
			id: 11,
			present: 0,
			unknown: 0,
			disappeared: 2,
			point: [12.48, 41.89],
			approximate: false,
			radius: null
		});
	});

	it('is absent when the geometry is redacted', () => {
		expect(locationFeature({ id: 11, geometry: null, approximate: false }, {})).toBeNull();
	});
});

describe('exploreHref', () => {
	it('selects the Location and puts the map on it, in the keys of the UI language', () => {
		const point: [number, number] = [12.4823, 41.8955];

		expect(exploreHref('/it/', { selection: 'superficie', viewport: 'mappa' }, 12, point)).toBe(
			`/it/?superficie=12&mappa=${RECORD_MAP_ZOOM}/41.89550/12.48230`
		);
		expect(exploreHref('/en/', { selection: 'location', viewport: 'map' }, 12, point)).toBe(
			'/en/?location=12&map=17/41.89550/12.48230'
		);
	});
});
