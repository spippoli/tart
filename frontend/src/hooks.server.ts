import { AsyncLocalStorage } from 'node:async_hooks';
import { sequence, type Handle, type HandleServerError } from '@sveltejs/kit/hooks';
import { chooseLanguage, LANGUAGE_COOKIE, textDirection } from '#lib/i18n/language.ts';
import { api, onBehalfOf, SESSION_COOKIE } from '#lib/server/api.ts';
import { readInstanceConfig } from '#lib/server/config.ts';
import { createContentSecurityPolicyHandle } from '#lib/server/content-security-policy.ts';
import { log } from '#lib/server/log.ts';
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
const resolveLanguage: Handle = async ({ event, resolve }) => {
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

/**
 * The signed-in User of every request, from the API, which reads the session and the
 * roles afresh each time: a revoked session or role takes effect on the next page.
 */
const resolveSession: Handle = async ({ event, resolve }) => {
	event.locals.user = null;
	if (event.cookies.get(SESSION_COOKIE)) {
		const { data, response } = await api().GET('/api/auth/session', {
			headers: onBehalfOf(event)
		});
		if (data === undefined) throw new Error(`GET /api/auth/session answered ${response.status}`);
		event.locals.user = data.user ?? null;
	}
	return resolve(event);
};

/** Every response carries the Content-Security-Policy, with the external map tile origins. */
export const handle = sequence(
	createContentSecurityPolicyHandle(readInstanceConfig),
	resolveSession,
	resolveLanguage
);

/**
 * An unexpected error is logged as one JSON line, with the path and never the query
 * string, the cookies, or the body; the page keeps SvelteKit's generic message. Errors
 * the app throws on purpose and SvelteKit's own (a 404) are not logged.
 */
export const handleError: HandleServerError = ({ kind, error, event }) => {
	if (kind !== 'unknown') return;
	log('error', error instanceof Error ? error.message : String(error), {
		path: event.url.pathname,
		...(error instanceof Error && error.stack ? { stack: error.stack } : {})
	});
};
