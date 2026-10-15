/**
 * Small rules of the Location entry (Discovery spec, Location entry without the
 * map) that are not drawing and not parsing: how a point is confirmed in words,
 * and the optional uncertainty radius.
 */
import type { Point } from './coordinates';

/** Digits shown for a coordinate: about 10 cm, far finer than any phone can say. */
const DIGITS = 6;

/** A latitude and a longitude as the confirmation prints them: "41.8986 N", "12.4769 E". */
export function describePoint(
	[lon, lat]: Point,
	locale: string
): { latitude: string; longitude: string } {
	const format = new Intl.NumberFormat(locale, { maximumFractionDigits: DIGITS });
	return {
		latitude: `${format.format(Math.abs(lat))} ${lat < 0 ? 'S' : 'N'}`,
		longitude: `${format.format(Math.abs(lon))} ${lon < 0 ? 'W' : 'E'}`
	};
}

/** The uncertainty radius in metres: empty for none, else a whole number above 0. */
export function parseRadius(text: string): { metres: number | null } | { error: 'invalid' } {
	const trimmed = text.trim();
	if (trimmed === '') return { metres: null };
	if (!/^\d+$/.test(trimmed)) return { error: 'invalid' };
	const metres = Number(trimmed);
	return metres > 0 && Number.isSafeInteger(metres) ? { metres } : { error: 'invalid' };
}
