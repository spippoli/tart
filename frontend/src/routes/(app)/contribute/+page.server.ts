import { fail, redirect } from '@sveltejs/kit';
import { localizeHref } from '#lib/paraglide/runtime.js';
import { api, onBehalfOf } from '#lib/server/api.ts';
import { refusal, signInAgain } from '#lib/server/contribution.ts';
import type { Actions, PageServerLoad } from './$types';

/**
 * The Contribute hub (Contribution and moderation spec, Contribute hub and My
 * contributions): start a new Artwork, the editorial guidelines and the licences of what
 * is contributed, and a link to My contributions. The hub is public; an anonymous user who
 * triggers a contribution action goes to sign-in and comes back to the hub.
 */
export const load: PageServerLoad = ({ locals }) => ({
	hasGuidelines: locals.config.texts.editorial_guidelines !== null,
	fileLicences: locals.config.licenses.files
});

export const actions: Actions = {
	/** Starts a draft of a new Artwork, then opens it in the editor. */
	start: async (event) => {
		if (!event.locals.user) signInAgain(event);
		const { data, error, response } = await api().POST('/api/contributions', {
			body: { target_kind: 'artwork' },
			headers: onBehalfOf(event)
		});
		if (response.status === 401) signInAgain(event);
		if (!data) return fail(response.status, refusal(error));
		redirect(303, localizeHref(`/contributions/${data.id}/edit`));
	}
};
