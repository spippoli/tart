import { error, fail, redirect } from '@sveltejs/kit';
import { signInHref } from '#lib/auth/next.ts';
import { localizeHref } from '#lib/paraglide/runtime.js';
import { api, onBehalfOf } from '#lib/server/api.ts';
import { refusal, signInAgain } from '#lib/server/contribution.ts';
import { isMergeIntent } from '#lib/server/merge-editor.ts';
import { vocabularies } from '#lib/server/records.ts';
import { mapSettings } from '#lib/server/map-settings.ts';
import type { Actions, PageServerLoad } from './$types';

/**
 * The Submission page as the Submitter sees it (Contribution and moderation spec,
 * Submission page): status in words, the proposed data, the Submission log, Decision
 * messages, and the Submitter's actions. The API answers 404 to anyone but the Submitter
 * and Moderators, and the log names a Moderator to no one else. An anonymous user goes to
 * sign-in and comes back.
 */

function submissionId(raw: string): number {
	if (!/^\d+$/.test(raw)) error(404);
	return Number(raw);
}

export const load: PageServerLoad = async (event) => {
	if (!event.locals.user) redirect(303, signInHref(event.url));
	const id = submissionId(event.params.id);
	const { data, response } = await api().GET('/api/contributions/{submission_id}', {
		params: { path: { submission_id: id } },
		headers: onBehalfOf(event)
	});
	if (response.status === 401) signInAgain(event);
	if (response.status === 404) error(404);
	if (!data) throw new Error(`contribution: ${response.status}`);
	// A Merge, Duplicate retirement, or Unmerge also shows its two records and the records its
	// approval rewrites, listed afresh for whoever reads the Submission.
	const merge =
		isMergeIntent(data.intent) && !data.stub
			? ((
					await api().GET('/api/contributions/{submission_id}/merge', {
						params: { path: { submission_id: id } },
						headers: onBehalfOf(event)
					})
				).data ?? null)
			: null;

	// What the last round changes, against the archive as it is now; the page reads without it.
	const compared =
		data.rounds > 0
			? await api().GET('/api/contributions/{submission_id}/comparison', {
					params: { path: { submission_id: id } },
					headers: onBehalfOf(event)
				})
			: undefined;
	return {
		submission: data,
		merge,
		...vocabularies(event),
		comparison: compared?.data ?? null,
		moderator: event.locals.user.moderator,
		// A Moderator reading someone else's Submission is offered none of the Submitter's actions.
		own: data.submitter.number === event.locals.user.number,
		decisionReasons: event.locals.config.vocabularies.decision_reasons,
		...mapSettings(event.locals)
	};
};

const VERDICTS = ['approve', 'reject', 'request_changes'] as const;

export const actions: Actions = {
	/** A Moderator adds a Moderation note: immutable, read by Moderators only. */
	note: async (event) => {
		const id = submissionId(event.params.id);
		const text = (await event.request.formData()).get('text')?.toString() ?? '';
		const {
			data,
			error: body,
			response
		} = await api().POST('/api/contributions/{submission_id}/notes', {
			params: { path: { submission_id: id } },
			body: { text },
			headers: onBehalfOf(event)
		});
		if (response.status === 401) signInAgain(event);
		if (!data) return fail(response.status, { section: 'note', ...refusal(body) });
		return { section: 'note', done: 'note' };
	},
	/** A Moderator approves, rejects, or asks for changes on the version they saw. */
	decide: async (event) => {
		const id = submissionId(event.params.id);
		const form = await event.request.formData();
		const verdict = VERDICTS.find((each) => each === form.get('verdict'));
		if (!verdict) return fail(400, { section: 'decision', code: 'unknown' });
		const reason = form.get('reason')?.toString() ?? '';
		const text = form.get('text')?.toString() ?? '';
		const {
			data,
			error: body,
			response
		} = await api().POST('/api/contributions/{submission_id}/decision', {
			params: { path: { submission_id: id } },
			// An approval takes no Decision message: whatever was typed is left out.
			body: {
				verdict,
				version: Number(form.get('version')),
				...(verdict === 'approve'
					? {}
					: { reason: reason === '' ? null : reason, text: text === '' ? null : text })
			},
			headers: onBehalfOf(event)
		});
		if (response.status === 401) signInAgain(event);
		if (!data) return fail(response.status, { section: 'decision', ...refusal(body) });
		return { section: 'decision', done: verdict };
	},
	retract: async (event) => {
		const id = submissionId(event.params.id);
		const {
			data,
			error: body,
			response
		} = await api().POST('/api/contributions/{submission_id}/retract', {
			params: { path: { submission_id: id } },
			headers: onBehalfOf(event)
		});
		if (response.status === 401) signInAgain(event);
		if (!data) return fail(response.status, refusal(body));
		return { retracted: true };
	},
	delete: async (event) => {
		const id = submissionId(event.params.id);
		const { error: body, response } = await api().DELETE('/api/contributions/{submission_id}', {
			params: { path: { submission_id: id } },
			headers: onBehalfOf(event)
		});
		if (response.status === 401) signInAgain(event);
		if (!response.ok) return fail(response.status, refusal(body));
		redirect(303, localizeHref('/account/contributions'));
	},
	startAgain: async (event) => {
		const id = submissionId(event.params.id);
		const {
			data,
			error: body,
			response
		} = await api().POST('/api/contributions/{submission_id}/start-again', {
			params: { path: { submission_id: id } },
			headers: onBehalfOf(event)
		});
		if (response.status === 401) signInAgain(event);
		if (!data) return fail(response.status, refusal(body));
		redirect(303, localizeHref(`/contributions/${data.id}/edit`));
	}
};
