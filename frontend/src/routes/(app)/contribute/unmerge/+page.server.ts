import { error, fail, redirect } from '@sveltejs/kit';
import { API_SEGMENTS, type Kind, type RevisionsView } from '#lib/archive/records.ts';
import { signInHref } from '#lib/auth/next.ts';
import { localizeHref } from '#lib/paraglide/runtime.js';
import { api, onBehalfOf } from '#lib/server/api.ts';
import { refusal, signInAgain } from '#lib/server/contribution.ts';
import { fetchView, vocabularies } from '#lib/server/records.ts';
import type { Actions, PageServerLoad } from './$types';

/**
 * The start of an Unmerge, or of the undoing of a Duplicate retirement (Contribution and
 * moderation spec, Merge, Duplicate retirement, Unmerge): a merged record's page of Revisions
 * links here, and starting opens the draft, pre-filled from the Revisions of the Merge, in
 * the editor.
 */
function recordOf(url: URL): { kind: Kind; id: number } {
	const kind = url.searchParams.get('kind') as Kind | null;
	const id = Number(url.searchParams.get('source'));
	if (!kind || !(kind in API_SEGMENTS) || !Number.isSafeInteger(id) || id < 1) error(404);
	return { kind, id };
}

export const load: PageServerLoad = async (event) => {
	if (!event.locals.user) redirect(303, signInHref(event.url));
	const { kind, id } = recordOf(event.url);
	const { data, response } = await fetchView<RevisionsView>(
		event,
		`/api/archive/${API_SEGMENTS[kind]}/${id}/revisions`
	);
	if (!data) error(response.status === 410 ? 410 : 404);
	return { view: data, ...vocabularies(event) };
};

export const actions: Actions = {
	start: async (event) => {
		if (!event.locals.user) signInAgain(event);
		const { id } = recordOf(event.url);
		const {
			data,
			error: body,
			response
		} = await api().POST('/api/contributions/unmerge', {
			body: { source_id: id },
			headers: onBehalfOf(event)
		});
		if (response.status === 401) signInAgain(event);
		if (!data) return fail(response.status, refusal(body));
		redirect(303, localizeHref(`/contributions/${data.id}/edit`));
	}
};
