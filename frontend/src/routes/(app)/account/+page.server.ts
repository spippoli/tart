import { fail, redirect, type RequestEvent } from '@sveltejs/kit';
import { signInHref } from '#lib/auth/next.ts';
import { localizeHref } from '#lib/paraglide/runtime.js';
import { api, onBehalfOf } from '#lib/server/api.ts';
import { clearSessionCookie } from '#lib/server/session-cookie.ts';
import type { Actions, PageServerLoad } from './$types';

/**
 * The Account page (Foundations spec, 2. Account): the display name, the preferred UI
 * language, the email address, the passkeys, and Sign out everywhere. Every action
 * answers with the `section` it belongs to, so that each section shows only its own
 * outcome. An anonymous user goes to sign-in and comes back.
 *
 * The email change takes two steps, as sign-in does: the new address, then the code
 * sent to it. Adding a passkey needs JavaScript: the page calls `passkeyOptions`,
 * lets the browser create a passkey, and posts it to `addPasskey`
 * (`#lib/auth/passkey.ts`); everything else works without it.
 */

export type Section = 'name' | 'language' | 'email' | 'passkeys';
export type EmailStep = 'email' | 'code';

function errorCode(error: unknown): string {
	return typeof error === 'object' && error !== null && 'code' in error
		? String(error.code)
		: 'unknown';
}

function field(form: FormData, name: string): string {
	return form.get(name)?.toString() ?? '';
}

/** A session that ended meanwhile sends the person to sign-in, then back here. */
function signInAgain(event: RequestEvent): never {
	redirect(303, signInHref({ pathname: event.url.pathname, search: '' }));
}

export const load: PageServerLoad = async (event) => {
	if (!event.locals.user) redirect(303, signInHref(event.url));
	const headers = onBehalfOf(event);
	const [account, passkeys] = await Promise.all([
		api().GET('/api/auth/account', { headers }),
		api().GET('/api/auth/passkeys', { headers })
	]);
	if (account.response.status === 401 || passkeys.response.status === 401) signInAgain(event);
	if (!account.data) throw new Error(`account: ${account.response.status}`);
	return {
		account: account.data,
		languages: event.locals.config.languages.ui,
		passkeys: passkeys.data ?? []
	};
};

async function changeAccount(
	event: RequestEvent,
	section: 'name' | 'language',
	body: { display_name?: string; preferred_language?: string }
) {
	const { data, error, response } = await api().PATCH('/api/auth/account', {
		body,
		headers: onBehalfOf(event)
	});
	if (response.status === 401) signInAgain(event);
	if (!data) return fail(400, { section, error: errorCode(error), ...body });
	return { section, saved: true };
}

export const actions: Actions = {
	displayName: async (event) => {
		const form = await event.request.formData();
		return changeAccount(event, 'name', { display_name: field(form, 'display_name') });
	},
	language: async (event) => {
		const form = await event.request.formData();
		return changeAccount(event, 'language', { preferred_language: field(form, 'language') });
	},
	requestEmailChange: async (event) => {
		const form = await event.request.formData();
		const email = field(form, 'email');
		const { error, response } = await api().POST('/api/auth/account/email', {
			body: { email },
			headers: onBehalfOf(event)
		});
		if (response.status === 401) signInAgain(event);
		if (response.status === 429 && error && 'retry_after' in error) {
			return fail(429, {
				section: 'email' as Section,
				step: 'email' as EmailStep,
				email,
				error: error.code,
				retryAfter: error.retry_after
			});
		}
		if (!response.ok) {
			return fail(400, {
				section: 'email' as Section,
				step: 'email' as EmailStep,
				email,
				error: errorCode(error)
			});
		}
		return { section: 'email' as Section, step: 'code' as EmailStep, email };
	},
	confirmEmailChange: async (event) => {
		const form = await event.request.formData();
		const email = field(form, 'email');
		const { data, error, response } = await api().POST('/api/auth/account/email/verify', {
			body: { code: field(form, 'code') },
			headers: onBehalfOf(event)
		});
		if (response.status === 401) signInAgain(event);
		if (!data) {
			return fail(400, {
				section: 'email' as Section,
				step: 'code' as EmailStep,
				email,
				error: errorCode(error)
			});
		}
		return { section: 'email' as Section, changed: data.email };
	},
	signOutEverywhere: async (event) => {
		await api().POST('/api/auth/sign-out-everywhere', { headers: onBehalfOf(event) });
		clearSessionCookie(event.cookies);
		redirect(303, localizeHref('/'));
	},
	passkeyOptions: async (event) => {
		const { data, response } = await api().POST('/api/auth/passkeys/options', {
			headers: onBehalfOf(event)
		});
		if (response.status === 401) signInAgain(event);
		if (!data) return fail(500, { section: 'passkeys' as Section, error: 'unknown' });
		return { options: data as unknown as PublicKeyCredentialCreationOptionsJSON };
	},
	addPasskey: async (event) => {
		const form = await event.request.formData();
		const name = field(form, 'name');
		let credential: Record<string, unknown>;
		try {
			credential = JSON.parse(field(form, 'credential'));
		} catch {
			return fail(400, { section: 'passkeys' as Section, error: 'passkey_invalid', name });
		}
		const { data, error, response } = await api().POST('/api/auth/passkeys', {
			body: { name, credential },
			headers: onBehalfOf(event)
		});
		if (response.status === 401) signInAgain(event);
		if (!data) return fail(400, { section: 'passkeys' as Section, error: errorCode(error), name });
		return { section: 'passkeys' as Section, added: data.name };
	},
	removePasskey: async (event) => {
		const form = await event.request.formData();
		const id = Number(form.get('id'));
		const { error, response } = await api().DELETE('/api/auth/passkeys/{passkey_id}', {
			params: { path: { passkey_id: id } },
			headers: onBehalfOf(event)
		});
		if (response.status === 401) signInAgain(event);
		if (!response.ok) {
			return fail(response.status, { section: 'passkeys' as Section, error: errorCode(error) });
		}
		return { section: 'passkeys' as Section, removed: field(form, 'name') };
	}
};
