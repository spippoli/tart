/**
 * The form of the editor of an existing record, and of a new Area or Artist (Contribution
 * and moderation spec, Submission form and Other editors), and its conversion to the working
 * copy the API stores: the archive's changeset in JSON (ADR 0007). An edit says only what
 * it changes: a field set, or an item of a collection added, changed, or removed. Nothing
 * here knows Svelte or the network.
 *
 * Everything the changeset can say lives in `operations`. The form itself is kept beside
 * them under `editor`, which the API stores with the copy and ignores, so that a draft
 * resumes exactly where it was left.
 */
import type { Kind } from '#lib/archive/records.ts';
import type { Geometry } from '#lib/map/drawing.ts';
import { parseRadius } from '#lib/map/location-entry.ts';
import { emptyDate, fromUncertainDate, toUncertainDate, type DateField } from '../date-field';
import type { SourceForm } from '../form';
import { SPECS, type CollectionSpec, type FieldSpec } from './spec';

export type Json = null | boolean | number | string | Json[] | { [key: string]: Json };
type Dict = { [key: string]: Json };

export interface PeriodField {
	start: DateField;
	end: DateField;
}
export interface TitleValue {
	text: string;
	untitled: boolean;
}
export interface PickedLocation {
	id: number;
	title: string;
}
export type SiteValue =
	{ kind: 'none' } | { kind: 'existing'; id: number; name: string } | { kind: 'new'; key: string };

export type FieldValue =
	| string
	| boolean
	| string[]
	| DateField
	| PeriodField
	| TitleValue
	| Geometry
	| PickedLocation
	| SiteValue
	| null;

/** A link to a record that exists (`id`), or to one this Submission creates (`key`). */
export interface LinkRef {
	id: number | null;
	key: string | null;
	name: string;
}

export interface LinkDelta {
	added: LinkRef[];
	removed: number[];
}

export interface ArtistChoice {
	kind: 'existing' | 'new';
	/** The Artist's id, or the key of the Artist this Submission creates. */
	id: number | null;
	key: string | null;
	name: string;
}

/** An Attribution being added, or one that exists and is being changed. */
export interface AttributionEdit {
	key: string;
	artist: ArtistChoice | null;
	certainty: 'confirmed' | 'probable' | 'disputed' | '';
	alias: string;
	note: string;
	/** Sources and Documentation items cited: records that exist, and Sources of this Submission. */
	citations: LinkRef[];
}

export interface CrewAdd {
	key: string;
	collective: { id: number; name: string } | null;
	period: PeriodField;
}

export interface NewSite {
	key: string;
	name: string;
	description: string;
	/** Keys of the Sources of this Submission. */
	sources: string[];
}
export type NewSeries = NewSite;
export interface NewArtist {
	key: string;
	name: string;
	artistKind: 'individual' | 'collective';
}

export interface RecordForm {
	/** The fields being set: all of them for a new record, those being edited for an edit. */
	fields: Record<string, FieldValue>;
	links: Record<string, LinkDelta>;
	aliases: { added: string[]; removed: string[] };
	attributions: {
		/** Existing Attributions being changed, by the Artist's id. */
		changed: Record<string, AttributionEdit>;
		removed: number[];
		added: AttributionEdit[];
	};
	crew: { added: CrewAdd[]; removed: number[] };
	/** The Sources this Submission creates, cited by the record and by what is created with it. */
	sources: SourceForm[];
	sites: NewSite[];
	series: NewSeries[];
	artists: NewArtist[];
	counter: number;
}

export function emptyRecordForm(): RecordForm {
	return {
		fields: {},
		links: {},
		aliases: { added: [], removed: [] },
		attributions: { changed: {}, removed: [], added: [] },
		crew: { added: [], removed: [] },
		sources: [],
		sites: [],
		series: [],
		artists: [],
		counter: 0
	};
}

export function nextRecordKey(form: RecordForm, prefix: string): string {
	form.counter += 1;
	return `${prefix}-${form.counter}`;
}

export function emptyPeriod(): PeriodField {
	return { start: emptyDate(), end: emptyDate() };
}

export function linkDelta(form: RecordForm, collection: string): LinkDelta {
	return (form.links[collection] ??= { added: [], removed: [] });
}

// ---- a field's value, to and from the record's JSON ----

const text = (value: unknown): string | null =>
	typeof value === 'string' && value.trim() !== '' ? value.trim() : null;
const str = (value: unknown): string => (typeof value === 'string' ? value : '');
const isDict = (value: unknown): value is Dict =>
	typeof value === 'object' && value !== null && !Array.isArray(value);

/** A reference in the changeset: an id, or the key of a record the changeset creates. */
const ref = (link: { id: number | null; key: string | null }): Json =>
	link.id !== null ? link.id : { new: link.key ?? '' };

export function dateJson(field: DateField, today: string): Json {
	return toUncertainDate(field, today).date as unknown as Json;
}

function periodJson(period: PeriodField, today: string): Json {
	const start = dateJson(period.start, today);
	const end = dateJson(period.end, today);
	return start === null && end === null ? null : { start, end };
}

/** The value of a field as the changeset says it. */
export function valueToJson(spec: FieldSpec, value: FieldValue, today: string): Json {
	switch (spec.type) {
		case 'text':
		case 'oneline':
		case 'multiline':
		case 'language':
			return text(value);
		case 'title': {
			const title = value as TitleValue;
			return title.untitled ? null : text(title.text);
		}
		case 'select':
			return text(value);
		case 'choices':
			return value as string[];
		case 'approximate':
			return value === true;
		case 'radius': {
			const parsed = parseRadius(str(value));
			return 'metres' in parsed ? parsed.metres : null;
		}
		case 'date':
			return dateJson(value as DateField, today);
		case 'period':
			return periodJson(value as PeriodField, today);
		case 'geometry':
			return value as unknown as Json;
		case 'site': {
			const site = value as SiteValue;
			return site.kind === 'none' ? null : site.kind === 'existing' ? site.id : { new: site.key };
		}
		case 'location':
			return (value as PickedLocation | null)?.id ?? null;
	}
}

/** What the record holds now, as the editor's value, to start an edit from (or from nothing). */
export function jsonToValue(
	spec: FieldSpec,
	json: unknown,
	names: (id: number) => string
): FieldValue {
	switch (spec.type) {
		case 'text':
		case 'oneline':
		case 'multiline':
		case 'language':
		case 'select':
			return str(json);
		case 'title':
			return { text: str(json), untitled: json === null || json === undefined };
		case 'choices':
			return Array.isArray(json)
				? json.filter((each): each is string => typeof each === 'string')
				: [];
		case 'approximate':
			return json === true;
		case 'radius':
			return typeof json === 'number' ? String(json) : '';
		case 'date':
			return isDict(json) ? fromUncertainDate(json as never) : emptyDate();
		case 'period':
			return isDict(json)
				? {
						start: isDict(json.start) ? fromUncertainDate(json.start as never) : emptyDate(),
						end: isDict(json.end) ? fromUncertainDate(json.end as never) : emptyDate()
					}
				: emptyPeriod();
		case 'geometry':
			return (isDict(json) ? json : null) as unknown as Geometry | null;
		case 'site':
			return typeof json === 'number'
				? { kind: 'existing', id: json, name: names(json) }
				: { kind: 'none' };
		case 'location':
			return typeof json === 'number' ? { id: json, title: names(json) } : null;
	}
}

/** The value a new record's form starts with, before anything is entered. */
export function initialValue(spec: FieldSpec): FieldValue {
	switch (spec.type) {
		case 'title':
			return { text: '', untitled: false };
		case 'choices':
			return [];
		case 'approximate':
			return false;
		case 'date':
			return emptyDate();
		case 'period':
			return emptyPeriod();
		case 'geometry':
		case 'location':
			return null;
		case 'site':
			return { kind: 'none' };
		default:
			return '';
	}
}

// ---- the changeset ----

export interface Subject {
	kind: Kind;
	/** The record an edit changes; `null` for a new record. */
	id: number | null;
}

const OP_SOURCE = 'source';

function createSources(form: RecordForm): Json[] {
	return form.sources.map((source): Json => ({
		op: 'create',
		ref: source.key,
		kind: OP_SOURCE,
		record: {
			title: text(source.title),
			author: text(source.author),
			publication: text(source.publication),
			url: text(source.url),
			note: text(source.note)
		}
	}));
}

function createInline(form: RecordForm): Json[] {
	const places = (kind: 'site' | 'series', each: NewSite): Json => ({
		op: 'create',
		ref: each.key,
		kind,
		record: {
			name: text(each.name),
			description: text(each.description),
			sources: each.sources.map((key) => ({ new: key }))
		}
	});
	return [
		...form.artists.map((artist): Json => ({
			op: 'create',
			ref: artist.key,
			kind: 'artist',
			record: { name: text(artist.name), kind: artist.artistKind }
		})),
		...form.sites.map((site) => places('site', site)),
		...form.series.map((series) => places('series', series)),
		...createSources(form)
	];
}

function attributionJson(each: AttributionEdit): Json {
	return {
		artist: each.artist ? ref(each.artist) : null,
		certainty: each.certainty || null,
		alias: text(each.alias),
		note: text(each.note),
		citations: each.citations.map(ref)
	};
}

function crewJson(each: CrewAdd, today: string): Json {
	return {
		collective: each.collective?.id ?? null,
		period: periodJson(each.period, today)
	};
}

/** The sources of a record that has a collection of them: the Submission's own, all cited. */
function sourceItems(form: RecordForm): LinkRef[] {
	return form.sources.map((each) => ({ id: null, key: each.key, name: each.title }));
}

/**
 * The operations of an edit, in an order that reads: the records created inline, then each
 * field set, then each collection's items removed and added.
 */
function editOperations(
	subject: Subject & { id: number },
	form: RecordForm,
	today: string,
	current: Dict
): Json[] {
	const spec = SPECS[subject.kind];
	const target = subject.id;
	const operations: Json[] = createInline(form);
	for (const field of spec.fields) {
		if (!(field.name in form.fields)) continue;
		operations.push({
			op: 'set',
			target,
			field: field.name,
			value: valueToJson(field, form.fields[field.name], today)
		});
	}
	for (const collection of spec.collections) {
		pushCollection(operations, collection, form, subject, today, current);
	}
	return operations;
}

function pushCollection(
	operations: Json[],
	collection: CollectionSpec,
	form: RecordForm,
	subject: Subject,
	today: string,
	current: Dict
) {
	const target = subject.id;
	const name = collection.name;
	switch (collection.type) {
		case 'links': {
			const delta = form.links[name] ?? { added: [], removed: [] };
			for (const id of delta.removed) {
				operations.push({ op: 'remove', target, collection: name, key: id });
			}
			const added = [...delta.added, ...(collection.picker === 'sources' ? sourceItems(form) : [])];
			for (const link of added) {
				operations.push({ op: 'add', target, collection: name, item: ref(link) });
			}
			return;
		}
		case 'aliases':
			for (const alias of form.aliases.removed) {
				operations.push({ op: 'remove', target, collection: name, key: alias });
			}
			for (const alias of form.aliases.added) {
				operations.push({ op: 'add', target, collection: name, item: alias });
			}
			return;
		case 'attributions': {
			for (const artist of form.attributions.removed) {
				operations.push({ op: 'remove', target, collection: name, key: artist });
			}
			for (const each of Object.values(form.attributions.changed)) {
				operations.push({ op: 'change', target, collection: name, item: attributionJson(each) });
			}
			for (const each of form.attributions.added) {
				operations.push({ op: 'add', target, collection: name, item: attributionJson(each) });
			}
			return;
		}
		case 'crew': {
			const memberships = Array.isArray(current[name]) ? (current[name] as Json[]) : [];
			for (const index of form.crew.removed) {
				const membership = memberships[index];
				if (isDict(membership)) {
					operations.push({
						op: 'remove',
						target,
						collection: name,
						key: [membership.collective, membership.period ?? null]
					});
				}
			}
			for (const each of form.crew.added) {
				operations.push({ op: 'add', target, collection: name, item: crewJson(each, today) });
			}
			return;
		}
	}
}

/** The record a new Area or Artist is, with its collections. */
function createOperations(subject: Subject, form: RecordForm, today: string): Json[] {
	const spec = SPECS[subject.kind];
	const record: Dict = {};
	for (const field of spec.fields) {
		record[field.name] = valueToJson(field, form.fields[field.name] ?? initialValue(field), today);
	}
	record.sources = sourceItems(form).map(ref);
	if (subject.kind === 'artist') {
		record.aliases = form.aliases.added;
		record.areas = (form.links.areas?.added ?? []).map(ref);
		record.crew_memberships = form.crew.added.map((each) => crewJson(each, today));
	}
	return [...createInline(form), { op: 'create', ref: 'record', kind: subject.kind, record }];
}

export interface Copy {
	[key: string]: Json | undefined;
}

/**
 * The working copy of the form, as the API stores it (never validated on save).
 * `current` is the record an edit changes, for the items it removes by position.
 */
export function toWorkingCopy(
	subject: Subject,
	form: RecordForm,
	today: string,
	current: Dict = {}
): Dict {
	const operations =
		subject.id === null
			? createOperations(subject, form, today)
			: editOperations({ ...subject, id: subject.id }, form, today, current);
	return {
		operations,
		initial_condition: null,
		editor: { kind: 'record', form: form as unknown as Json }
	};
}

/** The form a stored working copy holds; a copy this editor did not write gives an empty one. */
export function fromWorkingCopy(copy: unknown): RecordForm {
	const form = emptyRecordForm();
	if (!isDict(copy) || !isDict(copy.editor) || !isDict(copy.editor.form)) return form;
	const kept = copy.editor.form as unknown as Partial<RecordForm>;
	return { ...form, ...kept };
}

/** Whether the person has entered nothing: a draft just started. */
export function isBlankRecord(form: RecordForm): boolean {
	return (
		Object.keys(form.fields).length === 0 &&
		Object.values(form.links).every((each) => each.added.length + each.removed.length === 0) &&
		form.aliases.added.length + form.aliases.removed.length === 0 &&
		Object.keys(form.attributions.changed).length +
			form.attributions.removed.length +
			form.attributions.added.length ===
			0 &&
		form.crew.added.length + form.crew.removed.length === 0 &&
		form.sources.length === 0 &&
		form.sites.length + form.series.length + form.artists.length === 0
	);
}
