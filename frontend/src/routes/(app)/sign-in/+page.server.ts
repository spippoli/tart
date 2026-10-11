import { fail, redirect, type RequestEvent } from '@sveltejs/kit';
import { localizeHref } from '#lib/paraglide/runtime.js';
import { safeNext } from '#lib/auth/next.ts';
import { api, onBehalfOf } from '#lib/server/api.ts';
import { clearSessionCookie, relaySessionCookie } from '#lib/server/session-cookie.ts';
import type { Actions, PageServerLoad } from './$types';

/**
 * Sign-in by email code (Foundations spec, 2): the address, then the code, then, for
 * an address without a User, the registration step. Each step is a form action that
 * calls the API on the browser's behalf, so the page works without JavaScript.
 * Signing in with a passkey needs JavaScript: the page calls `passkeyOptions`, lets
 * the browser use a passkey, and posts it to `passkeySignIn` (`#lib/auth/passkey.ts`).
 */

export type Step = 'email' | 'code' | 'register';

function nextPage(event: RequestEvent, form?: FormData): string {
	const requested = form?.get('next')?.toString() ?? event.url.searchParams.get('next');
	return safeNext(requested, event.url.origin) ?? localizeHref('/');
}

/** The translatable error code of a refusal. */
function errorCode(error: unknown): string {
	return typeof error === 'object' && error !== null && 'code' in error
		? String(error.code)
		: 'unknown';
}

function field(form: FormData, name: string): string {
	return form.get(name)?.toString() ?? '';
}

export const load: PageServerLoad = (event) => {
	const { locals } = event;
	if (locals.user) redirect(303, nextPage(event));
	return {
		registration: locals.config.registration,
		minAge: locals.config.min_age,
		next: safeNext(event.url.searchParams.get('next'), event.url.origin)
	};
};

async function requestCode(event: RequestEvent) {
	const form = await event.request.formData();
	const email = field(form, 'email');
	const { response, error } = await api().POST('/api/auth/code', {
		body: { email, language: event.locals.locale, website: field(form, 'website') },
		headers: onBehalfOf(event)
	});
	if (response.status === 429 && error && 'retry_after' in error) {
		return fail(429, {
			step: 'email' as Step,
			email,
			error: error.code,
			retryAfter: error.retry_after
		});
	}
	if (!response.ok) {
		return fail(400, { step: 'email' as Step, email, error: errorCode(error) });
	}
	return { step: 'code' as Step, email };
}

async function verifyCode(event: RequestEvent, registering: boolean) {
	const form = await event.request.formData();
	const email = field(form, 'email');
	const code = field(form, 'code');
	const displayName = field(form, 'display_name');
	const { data, error, response } = await api().POST('/api/auth/code/verify', {
		body: {
			email,
			code,
			language: event.locals.locale,
			registration: registering
				? { display_name: displayName, age_confirmed: form.get('age_confirmed') === 'on' }
				: null
		},
		headers: onBehalfOf(event)
	});
	if (data?.outcome === 'registration_required') {
		return { step: 'register' as Step, email, code };
	}
	if (data?.outcome === 'signed_in') {
		relaySessionCookie(response, event.cookies);
		redirect(303, nextPage(event, form));
	}
	const reason = errorCode(error);
	// A wrong or expired code sends the person back to the code; anything else is the
	// registration step's own field.
	const step: Step = registering && reason !== 'code_invalid' ? 'register' : 'code';
	return fail(400, {
		step,
		email,
		code: step === 'register' ? code : '',
		displayName,
		error: reason
	});
}

async function passkeyOptions(event: RequestEvent) {
	const { data } = await api().POST('/api/auth/passkey/options', { headers: onBehalfOf(event) });
	if (!data) return fail(500, { step: 'email' as Step, error: 'unknown' });
	return { options: data as unknown as PublicKeyCredentialRequestOptionsJSON };
}

async function passkeySignIn(event: RequestEvent) {
	const form = await event.request.formData();
	let credential: Record<string, unknown>;
	try {
		credential = JSON.parse(field(form, 'credential'));
	} catch {
		return fail(400, { step: 'email' as Step, error: 'passkey_invalid' });
	}
	const { data, error, response } = await api().POST('/api/auth/passkey/verify', {
		body: { credential },
		headers: onBehalfOf(event)
	});
	if (data?.outcome === 'signed_in') {
		relaySessionCookie(response, event.cookies);
		redirect(303, nextPage(event, form));
	}
	return fail(400, { step: 'email' as Step, error: errorCode(error) });
}

export const actions: Actions = {
	request: requestCode,
	passkeyOptions,
	passkeySignIn,
	verify: (event) => verifyCode(event, false),
	register: (event) => verifyCode(event, true),
	signOut: async (event) => {
		await api().POST('/api/auth/sign-out', { headers: onBehalfOf(event) });
		clearSessionCookie(event.cookies);
		redirect(303, localizeHref('/'));
	}
};
