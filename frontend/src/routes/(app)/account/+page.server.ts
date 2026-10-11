import { fail, redirect, type RequestEvent } from '@sveltejs/kit';
import { signInHref } from '#lib/auth/next.ts';
import { api, onBehalfOf } from '#lib/server/api.ts';
import type { Actions, PageServerLoad } from './$types';

/**
 * The Account page (Foundations spec, 2. Account): for now its passkeys, which the
 * User lists, adds, and removes. Removing is a plain form; adding needs JavaScript:
 * the page calls `passkeyOptions`, lets the browser create a passkey, and posts it
 * to `addPasskey` (`#lib/auth/passkey.ts`). An anonymous user goes to sign-in and
 * comes back.
 */

function errorCode(error: unknown): string {
	return typeof error === 'object' && error !== null && 'code' in error
		? String(error.code)
		: 'unknown';
}

/** A session that ended meanwhile sends the person to sign-in, then back here. */
function signInAgain(event: RequestEvent): never {
	redirect(303, signInHref({ pathname: event.url.pathname, search: '' }));
}

export const load: PageServerLoad = async (event) => {
	if (!event.locals.user) redirect(303, signInHref(event.url));
	const { data, response } = await api().GET('/api/auth/passkeys', {
		headers: onBehalfOf(event)
	});
	if (response.status === 401) signInAgain(event);
	return { passkeys: data ?? [] };
};

export const actions: Actions = {
	passkeyOptions: async (event) => {
		const { data, response } = await api().POST('/api/auth/passkeys/options', {
			headers: onBehalfOf(event)
		});
		if (response.status === 401) signInAgain(event);
		if (!data) return fail(500, { error: 'unknown' });
		return { options: data as unknown as PublicKeyCredentialCreationOptionsJSON };
	},
	addPasskey: async (event) => {
		const form = await event.request.formData();
		const name = form.get('name')?.toString() ?? '';
		let credential: Record<string, unknown>;
		try {
			credential = JSON.parse(form.get('credential')?.toString() ?? '');
		} catch {
			return fail(400, { error: 'passkey_invalid', name });
		}
		const { data, error, response } = await api().POST('/api/auth/passkeys', {
			body: { name, credential },
			headers: onBehalfOf(event)
		});
		if (response.status === 401) signInAgain(event);
		if (!data) return fail(400, { error: errorCode(error), name });
		return { added: data.name };
	},
	removePasskey: async (event) => {
		const form = await event.request.formData();
		const id = Number(form.get('id'));
		const { error, response } = await api().DELETE('/api/auth/passkeys/{passkey_id}', {
			params: { path: { passkey_id: id } },
			headers: onBehalfOf(event)
		});
		if (response.status === 401) signInAgain(event);
		if (!response.ok) return fail(response.status, { error: errorCode(error) });
		return { removed: form.get('name')?.toString() ?? '' };
	}
};
