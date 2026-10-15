import { describe, expect, it } from 'vitest';
import { parseCoordinates, parseInInstance, type Point } from './coordinates';

// The fictional e2e boundary box, around Rome.
const BOUNDARY = [12.23, 41.65, 12.86, 42.14] as const;

function point(input: string): Point {
	const parsed = parseCoordinates(input);
	if (!('point' in parsed)) throw new Error(`${input}: ${parsed.error}`);
	return parsed.point;
}

// Discovery criterion 42: the field accepts all four input forms and rejects points outside the boundary.
describe('AC 42: the coordinates parser', () => {
	it('reads decimal degrees in the separators people type', () => {
		for (const text of [
			'41.8986, 12.4769',
			'41.8986,12.4769',
			' 41.8986 12.4769 ',
			'41,8986; 12,4769',
			'41,8986 12,4769'
		]) {
			expect(point(text)).toEqual([12.4769, 41.8986]);
		}
	});

	it('reads decimal degrees with hemisphere letters, in either order', () => {
		expect(point('41.8986 N, 12.4769 E')).toEqual([12.4769, 41.8986]);
		expect(point('12.4769E 41.8986N')).toEqual([12.4769, 41.8986]);
		expect(point('33.9 S, 18.4 E')).toEqual([18.4, -33.9]);
		expect(point('40.7 N 74.0 W')).toEqual([-74.0, 40.7]);
	});

	it('reads degrees-minutes-seconds', () => {
		for (const text of [
			`41°53'55"N 12°28'37"E`,
			`41°53′55″N, 12°28′37″E`,
			`41 53 55 N 12 28 37 E`,
			`N 41° 53' 55" E 12° 28' 37"`
		]) {
			const [lon, lat] = point(text);
			expect(lat).toBeCloseTo(41 + 53 / 60 + 55 / 3600, 6);
			expect(lon).toBeCloseTo(12 + 28 / 60 + 37 / 3600, 6);
		}
	});

	it('reads degrees and decimal minutes, and a south or west sign', () => {
		const [lon, lat] = point(`41°53.9'S 12°28.6'W`);
		expect(lat).toBeCloseTo(-(41 + 53.9 / 60), 6);
		expect(lon).toBeCloseTo(-(12 + 28.6 / 60), 6);
	});

	it('reads a geo: URI, ignoring altitude and parameters', () => {
		expect(point('geo:41.8986,12.4769')).toEqual([12.4769, 41.8986]);
		expect(point('geo:41.8986,12.4769,21;u=35')).toEqual([12.4769, 41.8986]);
	});

	it('reads OpenStreetMap links, preferring the marker to the view', () => {
		expect(point('https://www.openstreetmap.org/#map=17/41.8986/12.4769')).toEqual([
			12.4769, 41.8986
		]);
		expect(point('https://osm.org/?mlat=41.9&mlon=12.5#map=17/41.8986/12.4769')).toEqual([
			12.5, 41.9
		]);
	});

	it('reads Google Maps links: the pin, the query, the view', () => {
		expect(
			point('https://www.google.com/maps/place/Foo/@41.8,12.4,17z/data=!3d41.8986!4d12.4769')
		).toEqual([12.4769, 41.8986]);
		expect(point('https://www.google.com/maps?q=41.8986,12.4769')).toEqual([12.4769, 41.8986]);
		expect(point('https://www.google.com/maps/@41.8986,12.4769,18z')).toEqual([12.4769, 41.8986]);
	});

	it('explains a shortened link, which carries no coordinates', () => {
		expect(parseCoordinates('https://maps.app.goo.gl/AbC123')).toEqual({ error: 'short_link' });
	});

	it('says what is wrong rather than guessing', () => {
		expect(parseCoordinates('  ')).toEqual({ error: 'empty' });
		expect(parseCoordinates('Via dei Fori Imperiali')).toEqual({ error: 'unrecognised' });
		expect(parseCoordinates('https://example.org/41.8,12.4')).toEqual({ error: 'unrecognised' });
		expect(parseCoordinates('91.2, 12.4')).toEqual({ error: 'out_of_range' });
		expect(parseCoordinates('41.9, 181')).toEqual({ error: 'out_of_range' });
		expect(parseCoordinates(`41°75'00"N 12°28'37"E`)).toEqual({ error: 'unrecognised' });
		expect(parseCoordinates('41.9 N, 12.4 N')).toEqual({ error: 'unrecognised' });
	});

	it('rejects points outside the boundary with a code the form turns into a message', () => {
		expect(parseInInstance('41.8986, 12.4769', BOUNDARY)).toEqual({ point: [12.4769, 41.8986] });
		expect(parseInInstance('48.8566, 2.3522', BOUNDARY)).toEqual({ error: 'outside_boundary' });
		expect(parseInInstance('geo:0,0', BOUNDARY)).toEqual({ error: 'outside_boundary' });
		expect(parseInInstance('nonsense', BOUNDARY)).toEqual({ error: 'unrecognised' });
	});
});
