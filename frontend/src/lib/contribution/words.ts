/**
 * The words of a Submission: its status, its derived kind and labels, its log events, and
 * the refusals of the contribution API (Contribution and moderation spec, Lifecycle). The
 * vocabularies are closed (ADR 0009), so each has a message per value.
 */
import { formatWait, type FormatContext } from '#lib/i18n/format.ts';
import { m } from '#lib/paraglide/messages.js';
import { errorText as editorErrorText } from './errors.ts';
import type { components } from '../api/schema';

export type Status = components['schemas']['Status'];
export type SubmissionKind = components['schemas']['Kind'];

export const STATUSES: Status[] = [
	'draft',
	'submitted',
	'changes_requested',
	'approved',
	'rejected',
	'retracted'
];

const statusWords: Record<Status, () => string> = {
	draft: m.contribution_status_draft,
	submitted: m.contribution_status_submitted,
	changes_requested: m.contribution_status_changes_requested,
	approved: m.contribution_status_approved,
	rejected: m.contribution_status_rejected,
	retracted: m.contribution_status_retracted
};

export function statusText(status: Status): string {
	return statusWords[status]();
}

const kindWords: Record<'create' | 'edit', Partial<Record<SubmissionKind, () => string>>> = {
	create: {
		artwork: m.contribution_kind_create_artwork,
		location: m.contribution_kind_create_location,
		area: m.contribution_kind_create_area,
		artist: m.contribution_kind_create_artist
	},
	edit: {
		artwork: m.contribution_kind_edit_artwork,
		location: m.contribution_kind_edit_location,
		site: m.contribution_kind_edit_site,
		area: m.contribution_kind_edit_area,
		series: m.contribution_kind_edit_series,
		artist: m.contribution_kind_edit_artist,
		source: m.contribution_kind_edit_source,
		documentation_item: m.contribution_kind_edit_documentation_item
	}
};

export type Intent = components['schemas']['SubmissionSummary']['intent'];

const kindNouns: Record<SubmissionKind, () => string> = {
	artwork: m.archive_kind_artwork,
	location: m.archive_kind_location,
	site: m.archive_kind_site,
	area: m.archive_kind_area,
	series: m.archive_kind_series,
	source: m.archive_kind_source,
	documentation_item: m.archive_kind_documentation_item,
	artist: m.archive_kind_artist
};

/** "New Artwork", "Edit of an Artist", "Merge (Artist)": the derived kind, never chosen. */
export function kindText(intent: Intent, kind: SubmissionKind): string {
	if (intent === 'merge') return m.contribution_kind_merge({ kind: kindNouns[kind]() });
	if (intent === 'unmerge') return m.contribution_kind_unmerge({ kind: kindNouns[kind]() });
	if (intent === 'retirement') return m.contribution_kind_retirement();
	return (kindWords[intent][kind] ?? m.contribution_kind_other)();
}

const labelWords: Record<string, () => string> = {
	adds_documentation: m.contribution_label_adds_documentation,
	adds_history_event: m.contribution_label_adds_history_event,
	changes_attribution: m.contribution_label_changes_attribution,
	changes_condition: m.contribution_label_changes_condition
};

export function labelText(label: string): string {
	return (labelWords[label] ?? (() => label))();
}

const eventWords: Record<string, (inputs: { round: number; related: number }) => string> = {
	submitted: m.contribution_event_submitted,
	revised: m.contribution_event_revised,
	resubmitted: m.contribution_event_resubmitted,
	approved: m.contribution_event_approved,
	rejected: m.contribution_event_rejected,
	changes_requested: m.contribution_event_changes_requested,
	retracted: m.contribution_event_retracted,
	expired: m.contribution_event_expired,
	retry_of: m.contribution_event_retry_of,
	retried_in: m.contribution_event_retried_in,
	conversion_of: m.contribution_event_conversion_of,
	converted_into: m.contribution_event_converted_into
};

export function eventText(event: string, round: number | null, related: number | null): string {
	return (eventWords[event] ?? m.contribution_event_unknown)({
		round: round ?? 0,
		related: related ?? 0
	});
}

const errorWords: Record<string, () => string> = {
	'moderation.forbidden': m.contribution_error_forbidden,
	'moderation.not_submitter': m.contribution_error_not_submitter,
	'moderation.unknown_submission': m.contribution_error_unknown_submission,
	'moderation.invalid_transition': m.contribution_error_invalid_transition,
	'moderation.cannot_start_again': m.contribution_error_cannot_start_again,
	'moderation.outdated': m.contribution_error_outdated,
	'moderation.cannot_rebase': m.contribution_error_cannot_rebase,
	'moderation.target_withdrawn': m.contribution_error_target_withdrawn,
	'moderation.target_merged': m.contribution_error_target_merged,
	'moderation.drafts_limited': m.contribution_error_drafts_limited,
	'moderation.submissions_limited': m.contribution_error_submissions_limited,
	'moderation.uploads_limited': m.contribution_error_uploads_limited,
	'moderation.already_decided': m.moderation_error_already_decided,
	'moderation.own_submission': m.moderation_error_own_submission,
	'moderation.decision_reason_required': m.moderation_error_reason_required,
	'moderation.decision_text_required': m.moderation_error_text_required,
	'moderation.note_required': m.moderation_error_note_required,
	'moderation.approval_has_message': m.moderation_error_approval_has_message,
	moderator_only: m.moderation_error_moderator_only
};

/** A refusal of the API in words; a rate limit adds when it will be possible again. */
export function errorText(code: string, retryAfter: number | undefined, ctx: FormatContext) {
	const words = errorWords[code];
	// A rule of the archive that approval applied has the editor's words.
	const text = words ? words() : editorErrorText(code);
	return retryAfter === undefined
		? text
		: `${text} ${m.contribution_error_try_again({ wait: formatWait(retryAfter, ctx) })}`;
}
