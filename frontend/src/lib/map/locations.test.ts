import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import {
	geometryFeatures,
	hatchFeatures,
	prevailingGroup,
	signFeatures,
	signImageName,
	type LocationFeature,
	type LocationProperties
} from './locations';

function properties(values: Partial<LocationProperties> = {}): LocationProperties {
	return {
		id: 1,
		present: 0,
		unknown: 0,
		disappeared: 0,
		point: [12.5, 41.9],
		approximate: false,
		radius: null,
		...values
	};
}

const point = (values?: Partial<LocationProperties>): LocationFeature => ({
	type: 'Feature',
	geometry: { type: 'Point', coordinates: [12.5, 41.9] },
	properties: properties(values)
});

describe('the sign of a Location', () => {
	it('is present over unknown over disappeared', () => {
		expect(prevailingGroup(properties({ present: 1, unknown: 3, disappeared: 2 }))).toBe('present');
		expect(prevailingGroup(properties({ unknown: 1, disappeared: 4 }))).toBe('unknown');
		expect(prevailingGroup(properties({ disappeared: 2 }))).toBe('disappeared');
	});

	it('is stacked with more than one matching Artwork, and smaller when approximate', () => {
		expect(signImageName(properties({ present: 1 }))).toBe('sign-present-single-normal');
		expect(signImageName(properties({ present: 1, disappeared: 1 }))).toBe(
			'sign-present-stack-normal'
		);
		expect(signImageName(properties({ unknown: 1, approximate: true }))).toBe(
			'sign-unknown-single-small'
		);
	});

	it('sits at the representative point, with the count of its matching Artworks', () => {
		const line: LocationFeature = {
			type: 'Feature',
			geometry: {
				type: 'LineString',
				coordinates: [
					[12.5, 41.9],
					[12.52, 41.9]
				]
			},
			properties: properties({ id: 7, present: 2, point: [12.51, 41.9] })
		};
		const [sign] = signFeatures([line]);
		expect(sign.geometry.coordinates).toEqual([12.51, 41.9]);
		expect(sign.properties).toMatchObject({ id: 7, count: 2, group: 'present' });
	});
});

describe('geometries and the hatched area', () => {
	it('draws only the geometry of lines and polygons', () => {
		const line: LocationFeature = {
			type: 'Feature',
			geometry: {
				type: 'LineString',
				coordinates: [
					[12.5, 41.9],
					[12.52, 41.9]
				]
			},
			properties: properties({ id: 2, unknown: 1 })
		};
		const drawn = geometryFeatures([point({ id: 1, present: 1 }), line]);
		expect(drawn).toHaveLength(1);
		expect(drawn[0].properties).toEqual({ id: 2, group: 'unknown' });
	});

	it('hatches an approximate point with a radius, and only that', () => {
		const withRadius = point({ id: 1, present: 1, approximate: true, radius: 150 });
		const withoutRadius = point({ id: 2, present: 1, approximate: true });
		const exact = point({ id: 3, present: 1 });
		const hatched = hatchFeatures([withRadius, withoutRadius, exact]);
		expect(hatched.map((feature) => feature.properties.id)).toEqual([1]);
		const ring = hatched[0].geometry.coordinates[0];
		expect(ring[0]).toEqual(ring[ring.length - 1]);
		// 150 m east of the point, within a metre.
		const east = Math.max(...ring.map(([longitude]) => longitude)) - 12.5;
		expect(east * 111_320 * Math.cos((41.9 * Math.PI) / 180)).toBeCloseTo(150, 0);
	});
});

describe('the fictional Locations of the end-to-end tests', () => {
	const fixture = JSON.parse(
		readFileSync(new URL('../../../e2e/fixtures/map/locations.json', import.meta.url), 'utf8')
	) as { locations: LocationFeature[] };

	/** Squared distance from `p` to the segment `a`-`b`, in degrees. */
	function toSegment(p: number[], a: number[], b: number[]): number {
		const [dx, dy] = [b[0] - a[0], b[1] - a[1]];
		const t = Math.max(
			0,
			Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy))
		);
		return (p[0] - (a[0] + t * dx)) ** 2 + (p[1] - (a[1] + t * dy)) ** 2;
	}

	function inside(p: number[], ring: number[][]): boolean {
		let result = false;
		for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
			const [xi, yi] = ring[i];
			const [xj, yj] = ring[j];
			if (yi > p[1] !== yj > p[1] && p[0] < ((xj - xi) * (p[1] - yi)) / (yj - yi) + xi) {
				result = !result;
			}
		}
		return result;
	}

	it('have a representative point on their line and inside their polygon', () => {
		for (const { geometry, properties } of fixture.locations) {
			if (geometry.type === 'LineString') {
				const [a, b] = geometry.coordinates;
				expect(toSegment(properties.point, a, b)).toBeLessThan(1e-12);
			}
			if (geometry.type === 'Polygon') {
				expect(inside(properties.point, geometry.coordinates[0])).toBe(true);
			}
		}
		const shapes = fixture.locations.map(({ geometry }) => geometry.type);
		expect(shapes).toEqual(expect.arrayContaining(['LineString', 'Polygon']));
	});
});
