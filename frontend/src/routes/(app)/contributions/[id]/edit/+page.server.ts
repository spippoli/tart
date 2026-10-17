import { error, redirect } from '@sveltejs/kit';
import { locationTitleText, recordHref, vocabularyLabels } from '#lib/archive/records.ts';
import { signInHref } from '#lib/auth/next.ts';
import { artworkEditorOf } from '#lib/contribution/form.ts';
import type { RecordEditorConfig } from '#lib/contribution/record/state.svelte.ts';
import { localizeHref } from '#lib/paraglide/runtime.js';
import { api, onBehalfOf } from '#lib/server/api.ts';
import { isMergeIntent, loadMergeEditor } from '#lib/server/merge-editor.ts';
import { mapSettings } from '#lib/server/map-settings.ts';
import type { PageServerLoad } from './$types';

type Related = RecordEditorConfig['related'];

/**
 * The editor of a Submission (Contribution and moderation spec, Submission form and Other
 * editors). Only the Submitter reaches it (the API answers 404 to anyone else), and only
 * while the Submission can still be worked on: a draft, a `submitted` one being revised, or
 * one with changes requested. Any other state goes to the Submission page.
 *
 * Which editor opens is the Submission's: a new Artwork; documentation or a History event
 * added to an Artwork that exists; a new Area or Artist; or the edit of any record. An
 * edit starts from the record as it is stored (`/target`), with the words of what it links to.
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
	if (!['draft', 'submitted', 'changes_requested'].includes(submission.status)) {
		redirect(303, localizeHref(`/contributions/${id}`));
	}
	const merge = isMergeIntent(submission.intent) ? submission.intent : null;
	if (merge) {
		const { vocabularies } = event.locals.config;
		const context = {
			locale: event.locals.locale,
			timeZone: event.locals.config.geography.time_zone
		};
		return {
			editor: 'merge' as const,
			mergeEditor: await loadMergeEditor(event, submission, merge, terms.data, context),
			expressionTypes: vocabularies.expression_types,
			surfaceTypes: vocabularies.surface_types
		};
	}

	const { vocabularies, licenses } = event.locals.config;
	// The copy in progress, else the last submitted round to revise.
	const workingCopy = submission.working_copy ?? submission.last_round ?? null;
	const common = {
		submission: {
			id,
			status: submission.status,
			lastAutosave: submission.last_autosave_at ?? null
		},
		workingCopy,
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

	const kind = submission.target_kind;
	if (submission.intent === 'create') {
		if (kind === 'artwork')
			return { ...common, editor: 'artwork' as const, flavour: 'new' as const };
		if (kind === 'area' || kind === 'artist') {
			return {
				...common,
				editor: 'record' as const,
				kind,
				creating: true,
				targetId: null,
				current: {} as Record<string, never>,
				links: {},
				redactedFields: [] as string[],
				artworkCount: null,
				related: null as Related
			};
		}
		error(404);
	}

	// An edit: the record as it is stored, and the words of what it links to.
	const targetId = submission.target_id;
	if (targetId === null) error(404);
	const target = await api().GET('/api/contributions/{submission_id}/target', {
		params: { path: { submission_id: id } },
		headers
	});
	if (target.response.status === 404) error(404);
	if (!target.data) throw new Error(`the contribution API answered ${target.response.status}`);
	const record = target.data.record;

	if (kind === 'artwork') {
		const which = artworkEditorOf(workingCopy);
		if (which !== 'edit') {
			const title = typeof record.title === 'string' ? record.title : '';
			return {
				...common,
				editor: 'artwork' as const,
				flavour: which,
				target: { id: targetId, title }
			};
		}
	}

	return {
		...common,
		editor: 'record' as const,
		kind,
		creating: false,
		targetId,
		current: record as Record<string, unknown>,
		links: target.data.links,
		redactedFields: target.data.redacted_fields,
		artworkCount: target.data.artwork_count ?? null,
		related: await relatedOf(event, kind, targetId, record)
	};
};

/** The records that hold a membership in this one, listed read-only in its edit. */
async function relatedOf(
	event: Parameters<PageServerLoad>[0],
	kind: string,
	id: number,
	record: Record<string, unknown>
): Promise<Related> {
	const locale = event.locals.locale;
	const headers = onBehalfOf(event);
	if (kind === 'site') {
		const view = await api().GET('/api/archive/sites/{record_id}', {
			params: { path: { record_id: id } },
			headers
		});
		const surfaces = vocabularyLabels(event.locals.config.vocabularies.surface_types, locale);
		return {
			kind: 'locations',
			items: (view.data?.locations ?? []).map((each) => ({
				name: locationTitleText(each.id, each.title, surfaces, locale),
				href: recordHref('location', each.path, locale)
			}))
		};
	}
	if (kind === 'series') {
		const view = await api().GET('/api/archive/series/{record_id}', {
			params: { path: { record_id: id } },
			headers
		});
		return {
			kind: 'artworks',
			items: (view.data?.artworks ?? []).map((each) => ({
				name: each.title ?? '',
				href: recordHref('artwork', each.path, locale)
			}))
		};
	}
	if (kind === 'artist' && record.kind === 'collective') {
		const view = await api().GET('/api/archive/artists/{record_id}', {
			params: { path: { record_id: id } },
			headers
		});
		return {
			kind: 'members',
			items: (view.data?.members ?? []).map((each) => ({
				name: each.artist.name ?? '',
				href: recordHref('artist', each.artist.path, locale)
			}))
		};
	}
	return null;
}
