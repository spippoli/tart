import { error, redirect } from '@sveltejs/kit';
import { signInHref } from '#lib/auth/next.ts';
import { localizeHref } from '#lib/paraglide/runtime.js';
import { api, onBehalfOf } from '#lib/server/api.ts';
import { isMergeIntent, loadMergeEditor } from '#lib/server/merge-editor.ts';
import { mapSettings } from '#lib/server/map-settings.ts';
import type { PageServerLoad } from './$types';

/**
 * The editor of a new Artwork (Contribution and moderation spec, Submission form,
 * Routes). Only the Submitter reaches it (the API answers 404 to anyone else), and only
 * while the Submission can still be worked on: a draft, a `submitted` one being revised,
 * or one with changes requested. Any other state goes to the Submission page. The other
 * kinds of Submission have editors of their own: a Merge, a Duplicate retirement, and an
 * Unmerge share the Merge editor.
 */
export const load: PageServerLoad = async (event) => {
	if (!event.locals.user) redirect(303, signInHref(event.url));
	const id = Number(event.params.id);
	if (!Number.isSafeInteger(id) || id < 1) error(404);

	const headers = onBehalfOf(event);
	const [found, terms] = await Promise.all([
		api().GET('/api/contributions/{submission_id}', {
			params: { path: { submission_id: id } },
			headers
		}),
		api().GET('/api/contributions/terms', { headers })
	]);
	if (found.response.status === 401 || terms.response.status === 401) {
		redirect(303, signInHref(event.url));
	}
	if (found.response.status === 404) error(404);
	if (!found.data || !terms.data) {
		throw new Error(`the contribution API answered ${found.response.status}`);
	}
	const submission = found.data;
	const merge = isMergeIntent(submission.intent) ? submission.intent : null;
	if (!merge && (submission.target_kind !== 'artwork' || submission.intent !== 'create'))
		error(404);
	if (!['draft', 'submitted', 'changes_requested'].includes(submission.status)) {
		redirect(303, localizeHref(`/contributions/${id}`));
	}
	if (merge) {
		const { vocabularies } = event.locals.config;
		const context = {
			locale: event.locals.locale,
			timeZone: event.locals.config.geography.time_zone
		};
		return {
			kind: 'merge' as const,
			mergeEditor: await loadMergeEditor(event, submission, merge, terms.data, context),
			expressionTypes: vocabularies.expression_types,
			surfaceTypes: vocabularies.surface_types
		};
	}

	const { vocabularies, licenses } = event.locals.config;
	return {
		kind: 'artwork' as const,
		submission: {
			id,
			status: submission.status,
			lastAutosave: submission.last_autosave_at ?? null
		},
		// The copy in progress, else the last submitted round to revise.
		workingCopy: submission.working_copy ?? submission.last_round ?? null,
		terms: {
			version: terms.data.version,
			acceptedVersion: terms.data.accepted_version ?? null,
			acceptanceRequired: terms.data.acceptance_required
		},
		licences: licenses.files,
		expressionTypes: vocabularies.expression_types,
		surfaceTypes: vocabularies.surface_types,
		...mapSettings(event.locals)
	};
};
