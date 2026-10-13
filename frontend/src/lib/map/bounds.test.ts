import { describe, expect, it } from 'vitest';
import { BUFFER_METRES, MAX_ZOOM, mapBounds } from './bounds';

// The fictional e2e boundary box, around Rome.
const BOUNDARY = [12.23, 41.65, 12.86, 42.14] as const;

// Discovery criterion 64: no map pans beyond the boundary's box plus 2 km or zooms beyond z19.
describe('AC 64: map bounds and zoom', () => {
	it('buffers the boundary box by 2 km on every side', () => {
		const [west, south, east, north] = mapBounds(BOUNDARY);
		const metresPerDegreeLat = 110_574;
		expect((BOUNDARY[1] - south) * metresPerDegreeLat).toBeCloseTo(BUFFER_METRES, 0);
		expect((north - BOUNDARY[3]) * metresPerDegreeLat).toBeCloseTo(BUFFER_METRES, 0);
		// At the box's northern edge a degree of longitude is about 82.6 km.
		const metresPerDegreeLon = 111_320 * Math.cos((42.14 * Math.PI) / 180);
		expect((BOUNDARY[0] - west) * metresPerDegreeLon).toBeCloseTo(BUFFER_METRES, 0);
		expect((east - BOUNDARY[2]) * metresPerDegreeLon).toBeCloseTo(BUFFER_METRES, 0);
	});

	it('never covers less longitude than the buffer at any latitude of the box', () => {
		const [west] = mapBounds(BOUNDARY);
		const atSouth = 111_320 * Math.cos((41.65 * Math.PI) / 180);
		expect((BOUNDARY[0] - west) * atSouth).toBeGreaterThan(BUFFER_METRES);
	});

	it('works south of the equator', () => {
		const [, south, , north] = mapBounds([-43.8, -23.1, -43.1, -22.7]);
		expect(south).toBeLessThan(-23.1);
		expect(north).toBeGreaterThan(-22.7);
	});

	it('stops zooming in at z19', () => {
		expect(MAX_ZOOM).toBe(19);
	});
});
