/**
 * The coordinates parser of the Location entry (Discovery spec, Location entry
 * without the map). It reads a point out of text the contributor typed or pasted:
 * decimal degrees, degrees-minutes-seconds, a `geo:` URI, or an OpenStreetMap or
 * Google Maps link. It is not geocoding: it never looks anything up, and a link
 * that does not carry the coordinates (a shortened one) is an error.
 */
import type { Bounds } from './bounds';

/** Longitude, latitude (GeoJSON order). */
export type Point = readonly [number, number];

/**
 * Why text is not a point: nothing was entered, no known form matched, a
 * shortened map link carries no coordinates, a value is not a latitude and a
 * longitude, or the point lies outside the Instance.
 */
export type CoordinatesError =
	'empty' | 'unrecognised' | 'short_link' | 'out_of_range' | 'outside_boundary';

export type ParseResult = { point: Point } | { error: CoordinatesError };

const NUMBER = String.raw`\d+(?:[.,]\d+)?`;
const HEMISPHERE = String.raw`[NSEWnsew]`;

function toNumber(text: string): number {
	return Number(text.replace(',', '.'));
}

function valid([lon, lat]: Point): boolean {
	return (
		Number.isFinite(lon) && Number.isFinite(lat) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180
	);
}

function result(lat: number, lon: number): ParseResult {
	const point: Point = [lon, lat];
	return valid(point) ? { point } : { error: 'out_of_range' };
}

/** A latitude and a longitude from two decimal strings, e.g. `41.8986` and `12.4769`. */
function fromDecimals(first: string, second: string): ParseResult {
	return result(toNumber(first), toNumber(second));
}

// One component: 41.8986, 41°53'55.2", 41 53 55.2, 41d53m55s, with a sign or a
// hemisphere letter before (N 41°…) or after (41°…N) it.
const BODY = String.raw`(-)?(${NUMBER})(?:\s*(?:°|º|deg|d)\s*(?:(${NUMBER})\s*(?:['′’m]|\s)?\s*(?:(${NUMBER})\s*(?:["″”s]|'')?)?)?|\s+(${NUMBER})(?:\s+(${NUMBER}))?(?!\d))?`;
const BEFORE = new RegExp(String.raw`(${HEMISPHERE})\s*${BODY}`, 'iy');
const AFTER = new RegExp(String.raw`${BODY}\s*(${HEMISPHERE})?`, 'iy');

function component(
	text: string,
	from: number
): { value: number; axis?: 'ns' | 'ew'; end: number } | null {
	BEFORE.lastIndex = from;
	AFTER.lastIndex = from;
	const before = BEFORE.exec(text);
	let letter: string | undefined;
	let minus: string | undefined;
	let degrees: string;
	let minutes: string | undefined;
	let seconds: string | undefined;
	let whole: string;
	if (before) {
		whole = before[0];
		letter = before[1];
		[, , minus, degrees] = before;
		minutes = before[4] ?? before[6];
		seconds = before[5] ?? before[7];
	} else {
		const after = AFTER.exec(text);
		if (!after) return null;
		whole = after[0];
		[, minus, degrees] = after;
		minutes = after[3] ?? after[5];
		seconds = after[4] ?? after[6];
		letter = after[7];
	}
	const minuteValue = minutes === undefined ? 0 : toNumber(minutes);
	const secondValue = seconds === undefined ? 0 : toNumber(seconds);
	if (minuteValue >= 60 || secondValue >= 60) return null;
	letter = letter?.toUpperCase();
	let value = toNumber(degrees) + minuteValue / 60 + secondValue / 3600;
	if (minus || letter === 'S' || letter === 'W') value = -value;
	const axis = letter === undefined ? undefined : 'NS'.includes(letter) ? 'ns' : 'ew';
	return { value, axis, end: from + whole.length };
}

/** Two components, in either order when hemisphere letters say which is which. */
function parseTwoComponents(text: string): ParseResult | null {
	const clean = text.trim().replace(/\s+/g, ' ');
	const first = component(clean, 0);
	if (!first) return null;
	const rest = clean.slice(first.end).replace(/^\s*[,;]?\s*/, '');
	const offset = clean.length - rest.length;
	const second = component(clean, offset);
	if (!second || second.end !== clean.length) return null;
	if (first.axis && first.axis === second.axis) return null;
	if (first.axis === 'ew' || second.axis === 'ns') return result(second.value, first.value);
	return result(first.value, second.value);
}

/** `41.8986, 12.4769`, `41.8986 12.4769`, `41,8986; 12,4769`, with optional N/S/E/W. */
function parseDecimal(text: string): ParseResult | null {
	const clean = text.trim();
	const plain = new RegExp(
		String.raw`^(-?\d+(?:[.,]\d+)?)\s*(?:;|,\s+|,|\s)\s*(-?\d+(?:[.,]\d+)?)$`
	);
	const match = plain.exec(clean);
	if (match) {
		// "41,8986 12,4769" is two decimal-comma numbers; "41.8986,12.4769" two dotted ones.
		return fromDecimals(match[1], match[2]);
	}
	// With hemisphere letters the plain forms and the DMS forms share one reading.
	return parseTwoComponents(clean);
}

function parseGeoUri(text: string): ParseResult | null {
	const match = /^geo:(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)(?:,-?\d+(?:\.\d+)?)?(?:;.*)?$/i.exec(
		text.trim()
	);
	return match ? fromDecimals(match[1], match[2]) : null;
}

const PAIR = String.raw`(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)`;

function parseUrl(text: string): ParseResult | null {
	let url: URL;
	try {
		url = new URL(text.trim());
	} catch {
		return null;
	}
	if (url.protocol !== 'https:' && url.protocol !== 'http:') return null;
	const host = url.hostname.toLowerCase().replace(/^www\./, '');
	const query = url.searchParams;

	if (host === 'openstreetmap.org' || host === 'osm.org') {
		// The marker, when the link has one, is the point the sender meant.
		const mlat = query.get('mlat');
		const mlon = query.get('mlon');
		if (mlat !== null && mlon !== null) return fromDecimals(mlat, mlon);
		const fragment = /map=\d+(?:\.\d+)?\/(-?\d+(?:\.\d+)?)\/(-?\d+(?:\.\d+)?)/.exec(url.hash);
		if (fragment) return fromDecimals(fragment[1], fragment[2]);
		return { error: 'unrecognised' };
	}

	if (host === 'maps.app.goo.gl' || host === 'goo.gl') return { error: 'short_link' };

	if (/^(maps\.)?google\.[a-z.]+$/.test(host) || host === 'google.com') {
		// The place pin (`!3d…!4d…`) wins over the view centre (`@…`).
		const pin = /!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)/.exec(url.pathname + url.hash);
		if (pin) return fromDecimals(pin[1], pin[2]);
		for (const key of ['q', 'query', 'll', 'center', 'destination']) {
			const value = query.get(key);
			const pair = value && new RegExp(`^${PAIR}$`).exec(value.trim());
			if (pair) return fromDecimals(pair[1], pair[2]);
		}
		const centre = new RegExp(`@${PAIR}`).exec(url.pathname);
		if (centre) return fromDecimals(centre[1], centre[2]);
		return { error: 'unrecognised' };
	}
	return null;
}

/** Parses what the contributor entered; the result never depends on the UI language. */
export function parseCoordinates(input: string): ParseResult {
	const text = input.trim();
	if (text === '') return { error: 'empty' };
	return (
		parseGeoUri(text) ??
		parseUrl(text) ??
		parseDecimal(text) ??
		parseTwoComponents(text) ?? { error: 'unrecognised' }
	);
}

/** Whether a point lies within the bounding box of the Instance boundary. */
export function insideBounds([lon, lat]: Point, [west, south, east, north]: Bounds): boolean {
	return lon >= west && lon <= east && lat >= south && lat <= north;
}

/**
 * Parses and checks against the Instance. The client knows only the boundary's
 * bounding box; the server applies the polygon itself when the Submission is saved.
 */
export function parseInInstance(input: string, bounds: Bounds): ParseResult {
	const parsed = parseCoordinates(input);
	if ('error' in parsed) return parsed;
	return insideBounds(parsed.point, bounds) ? parsed : { error: 'outside_boundary' };
}
