import { error } from '@sveltejs/kit';
import type { components } from '../api/schema';
import type { Op } from '#lib/contribution/merge/ops.ts';
import type { ItemDetail, MergeConfig } from '#lib/contribution/merge/types.ts';
import type { Locale } from '#lib/paraglide/runtime.js';
import { api, onBehalfOf } from './api';

type Schemas = components['schemas'];

/** The intents whose editor is the Merge editor. */
export const MERGE_INTENTS = ['merge', 'retirement', 'unmerge'] as const;
export type MergeIntent = (typeof MERGE_INTENTS)[number];

export function isMergeIntent(intent: string): intent is MergeIntent {
	return (MERGE_INTENTS as readonly string[]).includes(intent);
}

async function detailOf(id: number, headers: Record<string, string>): Promise<ItemDetail | null> {
	const { data } = await api().GET('/api/archive/documents/{record_id}', {
		params: { path: { record_id: id } },
		headers
	});
	if (!data) return null;
	return {
		observed_date: data.observed_date,
		creator_credit: data.creator_credit,
		licence: data.licence,
		alt_text: data.alt_text
	};
}

/**
 * What the editor of a Merge, Duplicate retirement, or Unmerge needs: the Submission's
 * changeset, the API's review of the two records (the choices, the records to rewrite),
 * and for a retirement the two items side by side.
 */
export async function loadMergeEditor(
	event: Parameters<typeof onBehalfOf>[0],
	submission: Schemas['SubmissionOut'],
	intent: MergeIntent,
	terms: Schemas['TermsState'],
	context: { locale: Locale; timeZone: string }
): Promise<MergeConfig> {
	const headers = onBehalfOf(event);
	const { data: review, response } = await api().GET('/api/contributions/{submission_id}/merge', {
		params: { path: { submission_id: submission.id } },
		headers
	});
	if (!review) error(response.status === 404 ? 404 : 502);
	const copy = (submission.working_copy ?? submission.last_round ?? {}) as Record<string, unknown>;
	const { operations, ...rest } = copy;
	const details =
		intent === 'retirement'
			? {
					source: await detailOf(review.source.id, headers),
					into: await detailOf(review.into.id, headers)
				}
			: { source: null, into: null };
	return {
		submissionId: submission.id,
		intent,
		review,
		operations: (Array.isArray(operations) ? operations : []) as Op[],
		rest,
		lastAutosave: submission.last_autosave_at ?? null,
		locale: context.locale,
		timeZone: context.timeZone,
		terms: {
			version: terms.version,
			acceptedVersion: terms.accepted_version ?? null,
			acceptanceRequired: terms.acceptance_required
		},
		details
	};
}
