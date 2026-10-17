/**
 * What the editor of an existing record, or of a new Area or Artist, offers for each kind
 * (Contribution and moderation spec, Submission form and Other editors): the fields it
 * can change, the collections whose items it adds, changes, or removes, and the steps.
 * The record's own rules are the archive's; this says only what the form shows.
 */
import type { Kind } from '#lib/archive/records.ts';

export type FieldType =
	| 'text'
	| 'oneline'
	| 'multiline'
	| 'title'
	| 'select'
	| 'choices'
	| 'approximate'
	| 'radius'
	| 'date'
	| 'period'
	| 'geometry'
	| 'site'
	| 'location'
	| 'language';

export type Vocabulary = 'surface_types' | 'expression_types' | 'artist_kinds';

export interface FieldSpec {
	/** The field of the record, which is also the key of its message. */
	name: string;
	type: FieldType;
	/** Archive content, in the Content language (ADR 0008). */
	content?: boolean;
	/** The field cannot be left empty. */
	required?: boolean;
	vocabulary?: Vocabulary;
	/** For a geometry: the shape it may take. */
	shape?: 'polygon' | 'any';
	/** In a new record's form: the step that asks it. */
	step?: 'identity' | 'activity';
	/** For a Documentation item: the media whose field it is. */
	media?: readonly string[];
	/** For a date: it may stay empty. */
	optional?: boolean;
}

export type CollectionType = 'links' | 'aliases' | 'attributions' | 'crew';
export type PickerKind = 'series' | 'areas' | 'artworks' | 'artists' | 'sources';

export interface CollectionSpec {
	name: string;
	type: CollectionType;
	/** For links: what is picked. `sources` are the Submission's own, created in its Sources step. */
	picker?: PickerKind;
	step?: 'identity' | 'activity';
	/** The collection cannot be emptied (a Documentation item keeps one Artwork). */
	required?: boolean;
}

export interface KindSpec {
	fields: readonly FieldSpec[];
	collections: readonly CollectionSpec[];
	/** The steps of a new record, in order; an edit has `changes`, `sources`, `review`. */
	create?: readonly ('identity' | 'geometry' | 'activity' | 'sources' | 'review')[];
}

const SOURCES: CollectionSpec = { name: 'sources', type: 'links', picker: 'sources' };

export const SPECS: Record<Kind, KindSpec> = {
	artwork: {
		fields: [
			{ name: 'title', type: 'title', content: true },
			{ name: 'expression_types', type: 'choices', vocabulary: 'expression_types', required: true },
			{ name: 'description', type: 'multiline', content: true },
			{ name: 'location', type: 'location', required: true }
		],
		collections: [
			{ name: 'attributions', type: 'attributions' },
			{ name: 'series', type: 'links', picker: 'series' },
			SOURCES
		]
	},
	location: {
		fields: [
			{ name: 'geometry', type: 'geometry', shape: 'any', required: true },
			{ name: 'approximate', type: 'approximate' },
			{ name: 'uncertainty_radius', type: 'radius' },
			{ name: 'surface_type', type: 'select', vocabulary: 'surface_types', required: true },
			{ name: 'site', type: 'site' },
			{ name: 'place_description', type: 'oneline', content: true }
		],
		collections: []
	},
	site: {
		fields: [
			{ name: 'name', type: 'text', content: true, required: true },
			{ name: 'description', type: 'multiline', content: true }
		],
		collections: [SOURCES]
	},
	series: {
		fields: [
			{ name: 'name', type: 'text', content: true, required: true },
			{ name: 'description', type: 'multiline', content: true }
		],
		collections: [SOURCES]
	},
	area: {
		fields: [
			{ name: 'name', type: 'text', content: true, required: true, step: 'identity' },
			{ name: 'description', type: 'multiline', content: true, step: 'identity' },
			{ name: 'geometry', type: 'geometry', shape: 'polygon', required: true }
		],
		collections: [SOURCES],
		create: ['identity', 'geometry', 'sources', 'review']
	},
	artist: {
		fields: [
			{ name: 'name', type: 'text', content: true, required: true, step: 'identity' },
			{
				name: 'kind',
				type: 'select',
				vocabulary: 'artist_kinds',
				required: true,
				step: 'identity'
			},
			{ name: 'biography', type: 'multiline', content: true, step: 'identity' },
			{ name: 'period', type: 'period', step: 'activity' }
		],
		collections: [
			{ name: 'aliases', type: 'aliases', step: 'identity' },
			{ name: 'areas', type: 'links', picker: 'areas', step: 'activity' },
			{ name: 'crew_memberships', type: 'crew', step: 'activity' },
			SOURCES
		],
		create: ['identity', 'activity', 'sources', 'review']
	},
	source: {
		fields: [
			{ name: 'title', type: 'text', content: true, required: true },
			{ name: 'author', type: 'text', content: true },
			{ name: 'publication', type: 'text', content: true },
			{ name: 'date', type: 'date', optional: true },
			{ name: 'url', type: 'text' },
			{ name: 'note', type: 'multiline', content: true },
			{ name: 'language', type: 'language' }
		],
		collections: []
	},
	documentation_item: {
		fields: [
			{ name: 'observed_date', type: 'date', required: true },
			{ name: 'location', type: 'location', media: ['image', 'pdf', 'text', 'link'] },
			{ name: 'alt_text', type: 'multiline', content: true, media: ['image'] },
			{ name: 'language', type: 'language', media: ['text', 'link'] },
			{ name: 'text', type: 'multiline', content: true, media: ['text'] },
			{ name: 'url', type: 'text', media: ['link'] }
		],
		collections: [{ name: 'artworks', type: 'links', picker: 'artworks', required: true }]
	}
};

/** The fields of a Documentation item that never change; shown, not editable (spec, Other editors). */
export const FIXED_ITEM_FIELDS = [
	'medium',
	'file',
	'licence',
	'rights_basis',
	'creator_credit',
	'origin_url'
] as const;

/** The kinds a new record is created as a primary target here. */
export const CREATE_KINDS: readonly Kind[] = ['area', 'artist'];

/** The steps of an edit of the kind: What changes, Supporting Sources (when there is
 * something to cite), and Review and submit. */
export function editSteps(kind: Kind): readonly string[] {
	const sources =
		kind === 'artwork' ||
		kind === 'location' ||
		SPECS[kind].collections.some((c) => c.name === 'sources');
	return sources ? ['changes', 'sources', 'review'] : ['changes', 'review'];
}
