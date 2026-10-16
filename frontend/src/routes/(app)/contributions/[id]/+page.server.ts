import { error, fail, redirect } from '@sveltejs/kit';
import { signInHref } from '#lib/auth/next.ts';
import { localizeHref } from '#lib/paraglide/runtime.js';
import { api, onBehalfOf } from '#lib/server/api.ts';
import { refusal, signInAgain } from '#lib/server/contribution.ts';
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
	return {
		submission: data,
		// A Moderator reading someone else's Submission is offered none of the Submitter's actions.
		own: data.submitter.number === event.locals.user.number,
		decisionReasons: event.locals.config.vocabularies.decision_reasons
	};
};

export const actions: Actions = {
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
