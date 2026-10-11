import { describe, expect, it } from 'vitest';
import { formatDateTime, formatList, formatNumber, languageName } from './format';

// Foundations criterion 34: dates and numbers use Intl with the UI language and the Instance time zone.
describe('AC 34: locale-aware formatting', () => {
	it('formats numbers in the UI language', () => {
		expect(formatNumber(12345.5, { locale: 'it' })).toBe('12.345,5');
		expect(formatNumber(12345.5, { locale: 'en' })).toBe('12,345.5');
	});

	it('formats a date and time in the UI language and the Instance time zone', () => {
		// 23:30 UTC is already the next day in Rome (UTC+1 in winter).
		const instant = '2026-01-31T23:30:00Z';
		expect(formatDateTime(instant, { locale: 'it', timeZone: 'Europe/Rome' })).toBe(
			'1 febbraio 2026 alle ore 00:30'
		);
		expect(formatDateTime(instant, { locale: 'en', timeZone: 'Europe/Rome' })).toBe(
			'February 1, 2026 at 12:30 AM'
		);
		expect(formatDateTime(instant, { locale: 'en', timeZone: 'America/New_York' })).toBe(
			'January 31, 2026 at 6:30 PM'
		);
	});

	it('names languages and joins lists in the UI language', () => {
		expect(languageName('it', { locale: 'en' })).toBe('Italian');
		expect(languageName('en', { locale: 'it' })).toBe('inglese');
		expect(formatList(['italiano', 'inglese'], { locale: 'it' })).toBe('italiano e inglese');
	});
});
