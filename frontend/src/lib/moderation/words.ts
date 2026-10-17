/**
 * The words of the Moderation area: the queue's orders and filters, the review checklist,
 * and the compass points of a geometry comparison (Contribution and moderation spec, Queue,
 * Submission page). The vocabularies are closed, so each has a message per value.
 */
import { m } from '#lib/paraglide/messages.js';
import type { components } from '../api/schema';

export type Sort = components['schemas']['Sort'];
export type Verdict = components['schemas']['Verdict'];
export type Kind = components['schemas']['Kind'];

/** The only three orders of the queue; the first is the default. */
export const SORTS: Sort[] = ['oldest', 'newest', 'resubmitted'];

const sortWords: Record<Sort, () => string> = {
	oldest: m.moderation_queue_sort_oldest,
	newest: m.moderation_queue_sort_newest,
	resubmitted: m.moderation_queue_sort_resubmitted
};

export function sortText(sort: Sort): string {
	return sortWords[sort]();
}

/** The derived labels a Submission can carry: the queue filters on them. */
export const LABELS = [
	'adds_documentation',
	'adds_history_event',
	'changes_attribution',
	'changes_condition'
] as const;

/** The kinds of record a Submission is about. */
export const KINDS: Kind[] = [
	'artwork',
	'location',
	'site',
	'area',
	'series',
	'artist',
	'source',
	'documentation_item'
];

const kindWords: Record<Kind, () => string> = {
	artwork: m.archive_kind_artwork,
	location: m.archive_kind_location,
	site: m.archive_kind_site,
	area: m.archive_kind_area,
	series: m.archive_kind_series,
	artist: m.archive_kind_artist,
	source: m.archive_kind_source,
	documentation_item: m.archive_kind_documentation_item
};

export function kindName(kind: Kind): string {
	return kindWords[kind]();
}

/** The review checklist, in order; fixed by the platform and translated. */
export const CHECKLIST: (() => string)[] = [
	m.moderation_checklist_people,
	m.moderation_checklist_file_rights,
	m.moderation_checklist_artists,
	m.moderation_checklist_legality,
	m.moderation_checklist_evidence,
	m.moderation_checklist_location,
	m.moderation_checklist_duplicates,
	m.moderation_checklist_relevance
];

const directionWords: Record<string, () => string> = {
	N: m.moderation_direction_n,
	NE: m.moderation_direction_ne,
	E: m.moderation_direction_e,
	SE: m.moderation_direction_se,
	S: m.moderation_direction_s,
	SW: m.moderation_direction_sw,
	W: m.moderation_direction_w,
	NW: m.moderation_direction_nw
};

export function directionText(direction: string): string {
	return (directionWords[direction] ?? (() => direction))();
}
