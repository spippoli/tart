import { localizeHref } from '#lib/paraglide/runtime.js';

/**
 * The page to return to after signing in, from `?next=`: only a path on this site,
 * so that the sign-in page cannot be used as an open redirect. Null for anything else.
 */
export function safeNext(value: string | null | undefined, origin: string): string | null {
	if (!value || !value.startsWith('/') || value.startsWith('//') || value.includes('\\')) {
		return null;
	}
	let url: URL;
	try {
		url = new URL(value, origin);
	} catch {
		return null;
	}
	// Checked again after normalisation: dot segments collapse `/.//host` into `//host`.
	if (url.origin !== origin || url.pathname.startsWith('//')) {
		return null;
	}
	return url.pathname + url.search + url.hash;
}

/** The sign-in page, returning to `url` afterwards (Foundations spec, access rules). */
export function signInHref(url: { pathname: string; search: string }): string {
	const next = encodeURIComponent(url.pathname + url.search);
	return `${localizeHref('/sign-in')}?next=${next}`;
}
