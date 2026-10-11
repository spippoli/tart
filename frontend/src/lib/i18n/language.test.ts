import { describe, expect, it } from 'vitest';
import { chooseLanguage, textDirection } from './language';

// Foundations criterion 29: `/` redirects by cookie, then Accept-Language, then the default.
describe('AC 29: the root redirect language', () => {
	const enabled = ['it', 'en'];

	it('follows the cookie first', () => {
		expect(chooseLanguage({ cookie: 'en', acceptLanguage: 'it', enabled })).toBe('en');
	});

	it('ignores a cookie naming a language the Instance does not enable', () => {
		expect(chooseLanguage({ cookie: 'de', acceptLanguage: 'en', enabled })).toBe('en');
	});

	it('then follows Accept-Language by quality, matching the primary subtag', () => {
		expect(chooseLanguage({ cookie: undefined, acceptLanguage: 'en-GB,it;q=0.5', enabled })).toBe(
			'en'
		);
		expect(
			chooseLanguage({ cookie: undefined, acceptLanguage: 'it;q=0.4, en-US;q=0.9', enabled })
		).toBe('en');
		expect(chooseLanguage({ cookie: undefined, acceptLanguage: 'de, en;q=0.1', enabled })).toBe(
			'en'
		);
	});

	it('skips refused and unknown languages', () => {
		expect(chooseLanguage({ cookie: undefined, acceptLanguage: 'en;q=0, fr', enabled })).toBe('it');
	});

	it('falls back to the Instance default, the first enabled language', () => {
		expect(chooseLanguage({ cookie: undefined, acceptLanguage: null, enabled })).toBe('it');
		expect(chooseLanguage({ cookie: undefined, acceptLanguage: 'de', enabled: ['en', 'it'] })).toBe(
			'en'
		);
	});
});

describe('textDirection', () => {
	it('names the writing direction of a language', () => {
		expect(textDirection('it')).toBe('ltr');
		expect(textDirection('ar')).toBe('rtl');
	});
});
