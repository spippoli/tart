import { API_URL } from '$app/env/private';
import type { Cookies } from '@sveltejs/kit';
import { createApiClient } from '../api/client';

/** The cookie that holds the session the API issued (ADR 0005). */
export const SESSION_COOKIE = 'tart_session';

/**
 * Set by Caddy on every request with the client's address, and forwarded to the API,
 * which takes the client IP from nowhere else (Foundations spec, Rate limits).
 */
export const CLIENT_IP_HEADER = 'X-Tart-Client-IP';

let client: ReturnType<typeof createApiClient> | undefined;

/** The API, over the internal network (`API_URL`). */
export function api() {
	client ??= createApiClient({ baseUrl: API_URL });
	return client;
}

/** What a request to the API made on behalf of the browser carries: its session and its IP. */
export function onBehalfOf(event: {
	cookies: Cookies;
	getClientAddress: () => string;
}): Record<string, string> {
	const headers: Record<string, string> = { [CLIENT_IP_HEADER]: event.getClientAddress() };
	const session = event.cookies.get(SESSION_COOKIE);
	if (session) headers.cookie = `${SESSION_COOKIE}=${session}`;
	return headers;
}
