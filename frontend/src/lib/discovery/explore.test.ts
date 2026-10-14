import { describe, expect, it } from 'vitest';
import { EMPTY_MAP_DATA, type LocationFeature } from '#lib/map/locations.ts';
import {
	bboxParam,
	central,
	clampTo,
	contains,
	countsOf,
	extentOfSigns,
	viewOf,
	viewportOf,
	withSelection
} from './explore';

function sign(id: number, point: [number, number]): LocationFeature {
	return {
		type: 'Feature',
		geometry: { type: 'Point', coordinates: point },
		properties: {
			id,
			present: 1,
			unknown: 0,
			disappeared: 0,
			point,
			approximate: false,
			radius: null
		}
	};
}

describe('the viewport in the URL', () => {
	it('keeps a hundredth of a zoom level and five decimals of a degree', () => {
		expect(viewportOf(14.123456, [12.48234567, 41.89554321])).toEqual({
			zoom: 14.12,
			lat: 41.89554,
			lon: 12.48235
		});
	});

	it('is the view the map starts at', () => {
		expect(viewOf({ zoom: 15, lat: 41.9, lon: 12.5 })).toEqual({ center: [12.5, 41.9], zoom: 15 });
	});

	it('is sent to the list as west, south, east, north', () => {
		expect(bboxParam([12.1, 41.8, 12.9, 42.1])).toBe('12.1,41.8,12.9,42.1');
	});
});

describe('fitting to the results', () => {
	const boundary = [12.2, 41.6, 12.8, 42.1] as const;

	it('frames the signs', () => {
		expect(extentOfSigns([sign(1, [12.4, 41.8]), sign(2, [12.5, 41.9])])).toEqual([
			12.4, 41.8, 12.5, 41.9
		]);
		expect(extentOfSigns([])).toBeNull();
	});

	it('is cut to the boundary', () => {
		expect(clampTo([12.0, 41.5, 12.5, 41.9], boundary)).toEqual([12.2, 41.6, 12.5, 41.9]);
		expect(clampTo([13, 43, 14, 44], boundary)).toBeNull();
	});

	it('centres a Location near the edge of the view, not one in the middle', () => {
		const view = [0, 0, 10, 10] as const;
		expect(central(view, [5, 5])).toBe(true);
		expect(central(view, [1, 5])).toBe(false);
		expect(central(view, [5, 9.5])).toBe(false);
		expect(central(view, [20, 5])).toBe(false);
	});

	it('knows which points the viewport holds', () => {
		expect(contains([12, 41, 13, 42], [12.5, 41.5])).toBe(true);
		expect(contains([12, 41, 13, 42], [13.5, 41.5])).toBe(false);
	});
});

describe('the sign of a selection outside the filters', () => {
	const place = {
		id: 7,
		geometry: { type: 'Point', coordinates: [12.5, 41.9] },
		point: [12.5, 41.9] as [number, number],
		approximate: false
	};

	it('is added when no Artwork matching the filters is there', () => {
		const counts = countsOf([{ condition: { group: 'disappeared' } }]);
		const data = withSelection(EMPTY_MAP_DATA, place, counts);
		expect(data.locations.map(({ properties }) => properties.id)).toEqual([7]);
		expect(data.locations[0].properties).toMatchObject({ present: 0, disappeared: 1 });
	});

	it('is not doubled when the Location matches', () => {
		const data = { ...EMPTY_MAP_DATA, locations: [sign(7, [12.5, 41.9])] };
		expect(withSelection(data, place, countsOf([]))).toBe(data);
		expect(withSelection(data, null, countsOf([]))).toBe(data);
	});
});
