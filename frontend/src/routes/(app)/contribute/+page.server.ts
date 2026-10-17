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
		const form = await event.request.formData();
		const asked = form.get('kind');
		// A new Artwork from the hub, a new Area from the Areas page, a new Artist from the Artists page.
		const kind = asked === 'area' || asked === 'artist' ? asked : 'artwork';
		const { data, error, response } = await api().POST('/api/contributions', {
			body: { target_kind: kind },
			headers: onBehalfOf(event)
		});
		if (response.status === 401) signInAgain(event);
		if (!data) return fail(response.status, refusal(error));
		redirect(303, localizeHref(`/contributions/${data.id}/edit`));
	},

	/**
	 * Starts an edit of a record that exists (`flavour` edit), documentation added to an
	 * Artwork, or a History event on it (a report of a change in condition), then opens it.
	 * The editor to open is written into the draft's first working copy.
	 */
	edit: async (event) => {
		if (!event.locals.user) signInAgain(event);
		const form = await event.request.formData();
		const kind = String(form.get('kind') ?? '');
		const id = Number(form.get('id'));
		const flavour = String(form.get('flavour') ?? 'edit');
		if (!isKind(kind) || !Number.isSafeInteger(id) || id < 1) return fail(400, { code: 'unknown' });
		const headers = onBehalfOf(event);
		const { data, error, response } = await api().POST('/api/contributions', {
			body: { target_kind: kind, target_id: id },
			headers
		});
		if (response.status === 401) signInAgain(event);
		if (!data) return fail(response.status, refusal(error));
		// `facts` is the History event reached from "Propose an edit": all four groups of types.
		if (
			kind === 'artwork' &&
			(flavour === 'documentation' || flavour === 'event' || flavour === 'facts')
		) {
			const target = await api().GET('/api/contributions/{submission_id}/target', {
				params: { path: { submission_id: data.id } },
				headers
			});
			const title = typeof target.data?.record.title === 'string' ? target.data.record.title : '';
			await api().PUT('/api/contributions/{submission_id}/working-copy', {
				params: { path: { submission_id: data.id } },
				body: {
					content: {
						operations: [],
						editor: {
							flavour: flavour === 'facts' ? 'event' : flavour,
							target: { id, title },
							// "Report a condition change" offers the first three groups of event types.
							event: { report: flavour === 'event' }
						}
					}
				},
				headers
			});
		}
		redirect(303, localizeHref(`/contributions/${data.id}/edit`));
	}
};

const KINDS = [
	'artwork',
	'artist',
	'location',
	'site',
	'area',
	'series',
	'source',
	'documentation_item'
] as const;

function isKind(value: string): value is (typeof KINDS)[number] {
	return (KINDS as readonly string[]).includes(value);
}
