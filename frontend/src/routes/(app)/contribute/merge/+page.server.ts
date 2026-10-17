import { error, fail, redirect } from '@sveltejs/kit';
import { signInHref } from '#lib/auth/next.ts';
import { localizeHref } from '#lib/paraglide/runtime.js';
import { api, onBehalfOf } from '#lib/server/api.ts';
import { refusal, signInAgain } from '#lib/server/contribution.ts';
import { vocabularies } from '#lib/server/records.ts';
import type { Actions, PageServerLoad } from './$types';

/**
 * Step 1 of a Merge or a Duplicate retirement (Contribution and moderation spec, Merge
 * editor): the record to fold is the one the person came from, and the surviving record is
 * chosen among the likeliest ones (nearby Locations, alike names) or by its number. Choosing
 * starts the draft, pre-filled with the default Merge, and opens it in the editor.
 */
function sourceOf(url: URL): number {
	const id = Number(url.searchParams.get('source'));
	if (!Number.isSafeInteger(id) || id < 1) error(404);
	return id;
}

export const load: PageServerLoad = async (event) => {
	if (!event.locals.user) redirect(303, signInHref(event.url));
	const source = sourceOf(event.url);
	const { data, response } = await api().GET('/api/contributions/merge-candidates', {
		params: { query: { source_id: source } },
		headers: onBehalfOf(event)
	});
	if (response.status === 401) redirect(303, signInHref(event.url));
	if (!data) {
		if (response.status === 404) error(404);
		throw new Error(`the contribution API answered ${response.status}`);
	}
	return { source: data.source, candidates: data.items, ...vocabularies(event) };
};

export const actions: Actions = {
	/** Starts the Merge of the source into the chosen record. */
	start: async (event) => {
		if (!event.locals.user) signInAgain(event);
		const form = await event.request.formData();
		const source = Number(form.get('source'));
		const into = Number(form.get('into') || form.get('number'));
		if (!Number.isSafeInteger(into) || into < 1) return fail(422, { code: 'unknown' });
		const {
			data,
			error: body,
			response
		} = await api().POST('/api/contributions/merge', {
			body: { source_id: source, into_id: into },
			headers: onBehalfOf(event)
		});
		if (response.status === 401) signInAgain(event);
		if (!data) return fail(response.status, refusal(body));
		redirect(303, localizeHref(`/contributions/${data.id}/edit`));
	}
};
