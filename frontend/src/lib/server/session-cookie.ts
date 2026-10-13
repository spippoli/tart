import type { Cookies } from '@sveltejs/kit';
import { SESSION_COOKIE } from './api';

/**
 * Passes the session cookie the API set on its answer on to the browser, with the
 * same lifetime. The attributes are the API's: `HttpOnly`, `SameSite=Lax`, path `/`,
 * and `Secure`, which SvelteKit drops only on `http://localhost` in development.
 */
export function relaySessionCookie(response: Response, cookies: Cookies): boolean {
	for (const header of response.headers.getSetCookie()) {
		const [pair, ...attributes] = header.split(';');
		const separator = pair.indexOf('=');
		if (pair.slice(0, separator).trim() !== SESSION_COOKIE) continue;
		const maxAge = attributes
			.map((attribute) => attribute.trim().split('='))
			.find(([name]) => name.toLowerCase() === 'max-age')?.[1];
		cookies.set(SESSION_COOKIE, pair.slice(separator + 1).trim(), {
			path: '/',
			httpOnly: true,
			sameSite: 'lax',
			maxAge: maxAge === undefined ? undefined : Number(maxAge)
		});
		return true;
	}
	return false;
}

export function clearSessionCookie(cookies: Cookies): void {
	cookies.delete(SESSION_COOKIE, { path: '/', httpOnly: true, sameSite: 'lax' });
}
