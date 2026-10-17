import type { components } from '../../api/schema';
import type { Locale } from '#lib/paraglide/runtime.js';
import type { Op } from './ops';

export type MergeReview = components['schemas']['MergeReview'];

/** What the side-by-side view of two Documentation items shows of each. */
export interface ItemDetail {
	observed_date: unknown;
	creator_credit: string | null;
	licence: string | null;
	alt_text: string | null;
}

export interface MergeConfig {
	submissionId: number;
	intent: 'merge' | 'retirement' | 'unmerge';
	review: MergeReview;
	/** The changeset of the draft: the operations, in their JSON form. */
	operations: Op[];
	/** The rest of the working copy, which the editor keeps as it is. */
	rest: Record<string, unknown>;
	lastAutosave: string | null;
	locale: Locale;
	timeZone: string;
	terms: { version: number; acceptedVersion: number | null; acceptanceRequired: boolean };
	/** For a Duplicate retirement: the two items, side by side. */
	details: { source: ItemDetail | null; into: ItemDetail | null };
}
