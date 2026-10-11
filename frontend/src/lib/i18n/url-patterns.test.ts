import { describe, expect, it } from 'vitest';
import { deLocalizeHref, localizeHref, locales } from '#lib/paraglide/runtime.js';
import { urlPatterns } from './url-patterns';

describe('translated pathnames', () => {
	it('cover every platform UI language', () => {
		for (const { localized } of urlPatterns) {
			expect(localized.map(([language]) => language).sort()).toEqual([...locales].sort());
		}
	});

	it('prefix every page with its UI language and translate its segments', () => {
		expect(localizeHref('/about', { locale: 'it' })).toBe('/it/informazioni');
		expect(localizeHref('/about', { locale: 'en' })).toBe('/en/about');
		expect(localizeHref('/about/data-licence', { locale: 'it' })).toBe(
			'/it/informazioni/licenza-dati'
		);
		expect(localizeHref('/', { locale: 'en' })).toBe('/en/');
		expect(localizeHref('/archive?q=muro', { locale: 'it' })).toBe('/it/archivio?q=muro');
	});

	it('map a localized path back to its route', () => {
		expect(deLocalizeHref('/it/informazioni/tart')).toBe('/about/tart');
		expect(deLocalizeHref('/en/about/terms')).toBe('/about/terms');
		expect(deLocalizeHref('/it/')).toBe('/');
		expect(deLocalizeHref('/it')).toBe('/');
		expect(deLocalizeHref('/en/not-a-page')).toBe('/not-a-page');
	});

	it('keep the same page across UI languages', () => {
		const english = localizeHref(deLocalizeHref('/it/informazioni/contatti'), { locale: 'en' });
		expect(english).toBe('/en/about/contact');
	});
});
