import { AsyncLocalStorage } from 'node:async_hooks';
import type { Handle } from '@sveltejs/kit/hooks';
import { chooseLanguage, LANGUAGE_COOKIE, textDirection } from '#lib/i18n/language.ts';
import { readInstanceConfig } from '#lib/server/config.ts';
import {
	isLocale,
	localizeHref,
	overwriteServerAsyncLocalStorage,
	type Locale
} from '#lib/paraglide/runtime.js';

type Store = { locale?: Locale; origin?: string; messageCalls?: Set<string> };

// Paraglide reads the UI language of the request being rendered from here.
const requestStore = new AsyncLocalStorage<Store>();
overwriteServerAsyncLocalStorage(requestStore);

/**
 * Resolves the UI language of every request (ADR 0008): only `/` redirects, by
 * cookie, then `Accept-Language`, then the Instance default; every other URL
 * names its language in its prefix, and a prefix that is not an enabled UI
 * language makes the page answer 404, rendered in the Instance default.
 */
export const handle: Handle = async ({ event, resolve }) => {
	const config = await readInstanceConfig();
	const enabled = config.languages.ui.filter(isLocale);
	const defaultLocale = enabled[0];
	const origin = event.url.origin;

	if (event.url.pathname === '/') {
		const language = chooseLanguage({
			cookie: event.cookies.get(LANGUAGE_COOKIE),
			acceptLanguage: event.request.headers.get('accept-language'),
			enabled
		}) as Locale;
		const location = requestStore.run({ locale: language, origin }, () =>
			localizeHref('/', { locale: language })
		);
		return new Response(null, {
			status: 302,
			headers: { location: location + event.url.search, vary: 'Cookie, Accept-Language' }
		});
	}

	const prefix = event.url.pathname.split('/')[1];
	const languageEnabled = (enabled as string[]).includes(prefix);
	const locale = languageEnabled ? (prefix as Locale) : defaultLocale;
	event.locals.config = config;
	event.locals.locale = locale;
	event.locals.languageEnabled = languageEnabled;

	return requestStore.run({ locale, origin, messageCalls: new Set() }, () =>
		resolve(event, {
			transformPageChunk: ({ html }) =>
				html.replace('%tart.lang%', locale).replace('%tart.dir%', textDirection(locale))
		})
	);
};
