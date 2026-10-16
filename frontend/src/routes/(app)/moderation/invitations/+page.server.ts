import { error, fail, redirect, type RequestEvent } from '@sveltejs/kit';
import { signInHref } from '#lib/auth/next.ts';
import { api, onBehalfOf } from '#lib/server/api.ts';
import type { Actions, PageServerLoad } from './$types';

/**
 * The Invitations page (Contribution and moderation spec, Invitations): issue, list, and
 * revoke. It answers 404 unless the Instance registers by invitation; the Moderation
 * layout has already turned away anonymous users and non-Moderators.
 */

function errorCode(body: unknown): string {
	return typeof body === 'object' && body !== null && 'code' in body
		? String(body.code)
		: 'unknown';
}

/** A session that ended meanwhile sends the person to sign-in, then back here. */
function signInAgain(event: RequestEvent): never {
	redirect(303, signInHref({ pathname: event.url.pathname, search: '' }));
}

export const load: PageServerLoad = async (event) => {
	if (event.locals.config.registration !== 'invite') error(404);
	const { data, response } = await api().GET('/api/moderation/invitations', {
		headers: onBehalfOf(event)
	});
	if (response.status === 401) signInAgain(event);
	if (response.status === 403) error(403, { message: 'Forbidden', reason: 'moderator_only' });
	if (!data) throw new Error(`invitations: ${response.status}`);
	return { invitations: data.items };
};

export const actions: Actions = {
	issue: async (event) => {
		const email = (await event.request.formData()).get('email')?.toString() ?? '';
		const {
			data,
			error: body,
			response
		} = await api().POST('/api/moderation/invitations', {
			body: { email },
			headers: onBehalfOf(event)
		});
		if (response.status === 401) signInAgain(event);
		if (!data) return fail(response.status, { section: 'issue', error: errorCode(body), email });
		return { section: 'issue', issued: { email: data.email, expiresAt: data.expires_at } };
	},
	revoke: async (event) => {
		const form = await event.request.formData();
		const { error: body, response } = await api().POST(
			'/api/moderation/invitations/{invitation_id}/revoke',
			{
				params: { path: { invitation_id: Number(form.get('id')) } },
				headers: onBehalfOf(event)
			}
		);
		if (response.status === 401) signInAgain(event);
		if (!response.ok) return fail(response.status, { section: 'list', error: errorCode(body) });
		return { section: 'list', revoked: form.get('email')?.toString() ?? '' };
	}
};
