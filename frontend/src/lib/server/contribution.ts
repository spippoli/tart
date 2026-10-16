import { redirect, type RequestEvent } from '@sveltejs/kit';
import { signInHref } from '#lib/auth/next.ts';

/** The stable code (and the wait, for a rate limit) of a refusal by the contribution API. */
export function refusal(body: unknown): { code: string; retryAfter?: number } {
	if (typeof body !== 'object' || body === null || !('code' in body)) return { code: 'unknown' };
	const retryAfter = 'retry_after' in body ? Number(body.retry_after) : undefined;
	return { code: String(body.code), ...(retryAfter === undefined ? {} : { retryAfter }) };
}

/** A session that ended meanwhile sends the person to sign-in, then back here. */
export function signInAgain(event: Pick<RequestEvent, 'url'>): never {
	redirect(303, signInHref({ pathname: event.url.pathname, search: '' }));
}
