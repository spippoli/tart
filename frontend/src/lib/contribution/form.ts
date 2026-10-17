/**
 * The editor's form for a new Artwork (Contribution and moderation spec, Submission
 * form) and its two conversions: to the working copy the API stores (`{operations,
 * initial_condition}`, the archive's changeset in JSON, ADR 0007) and back from it, so
 * that a draft resumes where it was left. Nothing here knows Svelte or the network.
 *
 * Everything the changeset can say lives in `operations`. What it cannot (that the title
 * is explicitly *Untitled*, the names of the records a link points to, the confirmations
 * of the duplicate warning) is kept under `editor`, which the API stores with the copy
 * and ignores.
 */
import type { UncertainDate } from '#lib/archive/uncertain-date.ts';
import type { Geometry } from '#lib/map/drawing.ts';
import { emptyDate, fromUncertainDate, toUncertainDate, type DateField } from './date-field';
export const STEPS = [
	'location',
	'documentation',
	'artwork',
	'attribution',
	'creation',
	'sources',
	'review'
] as const;
export type Step = (typeof STEPS)[number] | 'change' | 'event' | 'evidence';

/**
 * What the Artwork editor is for. A new Artwork walks the seven steps; the other two
 * attach to an Artwork that exists (Contribution and moderation spec, Form structure):
 * *documentation* adds Documentation items and may report that they show a change, and
 * *event* adds a History event with its evidence (a condition change or a disappearance).
 */
export type Flavour = 'new' | 'documentation' | 'event';
export const FLAVOUR_STEPS: Record<Flavour, readonly Step[]> = {
	new: STEPS,
	documentation: ['documentation', 'change', 'sources', 'review'],
	event: ['event', 'evidence', 'review']
};

/** The History event types of the form, by group (Submission form, History event type groups). */
export const EVENT_GROUPS = [
	{ group: 'observed', types: ['condition_recorded'] },
	{ group: 'change', types: ['deteriorated', 'damaged', 'modified'] },
	{ group: 'disappearance', types: ['covered', 'removed', 'destroyed'] },
	{ group: 'other', types: ['created', 'attribution_changed'] }
] as const;
export type EventType = (typeof EVENT_GROUPS)[number]['types'][number];
/** "Report a condition change" opens the first three groups only; the last is reached from an edit. */
export const REPORT_GROUPS = ['observed', 'change', 'disappearance'] as const;

/** Conditions grouped as the initial Condition asks them (ADR 0015). */
export const CONDITION_GROUPS = [
	{ group: 'present', conditions: ['intact', 'deteriorated', 'damaged', 'modified'] },
	{ group: 'disappeared', conditions: ['covered', 'removed', 'destroyed', 'missing'] },
	{ group: 'unknown', conditions: ['unknown'] }
] as const;
export type Condition = (typeof CONDITION_GROUPS)[number]['conditions'][number];

/** At most this many uploaded Documentation items in one Submission; links do not count. */
export const MAX_UPLOADED = 20;
export const ALT_TEXT_MAX = 250;
export const PLACE_DESCRIPTION_MAX = 200;

export type Certainty = 'confirmed' | 'probable' | 'disputed';
export type RightsBasis = 'own_work' | 'third_party';
export type DocMedium = 'image' | 'pdf' | 'link';
export type ArtistKind = 'individual' | 'collective';

export interface LocationForm {
	/** An existing Location chosen, to put the Artwork on. */
	existing: { id: number; title: string } | null;
	/** The geometry of a new Location, once finished. */
	geometry: Geometry | null;
	approximate: boolean;
	/** In metres; allowed on an approximate point only. */
	radius: number | null;
	surfaceType: string;
	placeDescription: string;
	/** The placement the duplicate warning was confirmed for ("different surface" or "different Artwork"). */
	confirmedKey: string | null;
}

export interface DocForm {
	key: string;
	medium: DocMedium;
	/** The id of the upload, for an image or a PDF. */
	file: string | null;
	fileName: string;
	observed: DateField;
	/** The Observed date came from the file's EXIF capture date: a suggestion. */
	suggested: boolean;
	rightsBasis: RightsBasis | '';
	creatorCredit: string;
	licence: string;
	originUrl: string;
	altText: string;
	url: string;
}

export type ArtistChoice =
	| { kind: 'existing'; id: number; name: string }
	| { kind: 'new'; key: string; name: string; artistKind: ArtistKind };

export interface AttributionForm {
	key: string;
	artist: ArtistChoice | null;
	certainty: Certainty | '';
	alias: string;
	note: string;
	/** Keys of the Sources and Documentation items of this Submission. */
	citations: string[];
}

export interface SeriesChoice {
	/** An existing Series, or a new one named by `key`. */
	id: number | null;
	key: string | null;
	name: string;
}

export interface SourceForm {
	key: string;
	title: string;
	author: string;
	publication: string;
	url: string;
	note: string;
}

/** The History event of the other two flavours of the editor. */
export interface EventForm {
	/** Add documentation: whether the new files show a change; `null`, not answered yet. */
	shows: boolean | null;
	type: EventType | '';
	observed: DateField;
	/** The Condition a `condition recorded` event states. */
	condition: Condition | '';
	note: string;
	/** The Artwork covering this one, for a `covered` event. */
	covering: { id: number; title: string } | null;
	/** Opened by "Report a condition change": the first three groups of types only. */
	report: boolean;
}

export function emptyEvent(): EventForm {
	return {
		shows: null,
		type: '',
		observed: emptyDate(),
		condition: '',
		note: '',
		covering: null,
		report: false
	};
}

export interface ArtworkForm {
	/** The existing Artwork a documentation or event Submission is about. */
	target: { id: number; title: string } | null;
	event: EventForm;
	location: LocationForm;
	documentation: DocForm[];
	initialCondition: Condition | '';
	title: string;
	untitled: boolean;
	expressionTypes: string[];
	description: string;
	series: SeriesChoice[];
	/** `null`: not chosen yet; `false`: unknown authorship, said explicitly. */
	attributed: boolean | null;
	attributions: AttributionForm[];
	created: { date: DateField; citations: string[] };
	sources: SourceForm[];
	counter: number;
}

export function emptyForm(): ArtworkForm {
	return {
		target: null,
		event: emptyEvent(),
		location: {
			existing: null,
			geometry: null,
			approximate: false,
			radius: null,
			surfaceType: '',
			placeDescription: '',
			confirmedKey: null
		},
		documentation: [],
		initialCondition: '',
		title: '',
		untitled: false,
		expressionTypes: [],
		description: '',
		series: [],
		attributed: null,
		attributions: [],
		created: { date: emptyDate(), citations: [] },
		sources: [],
		counter: 0
	};
}

/** A key for a new record of this Submission, unique within it. */
export function nextKey(form: ArtworkForm, prefix: string): string {
	form.counter += 1;
	return `${prefix}-${form.counter}`;
}

/** What identifies a placement for the duplicate warning: a Location, or a place drawn. */
export function placementKey(location: LocationForm): string | null {
	if (location.existing) return `location:${location.existing.id}`;
	if (!location.geometry) return null;
	return `new:${JSON.stringify(location.geometry)}:${location.radius ?? ''}`;
}

/** The Sources and Documentation items a Claim can cite, with a word for each. */
export interface Citable {
	key: string;
	kind: 'source' | 'documentation';
	label: string;
}

type Json = null | boolean | number | string | Json[] | { [key: string]: Json };
type Dict = { [key: string]: Json };

const text = (value: string): string | null => (value.trim() === '' ? null : value.trim());
const ref = (key: string): Json => ({ new: key });

const LOCATION = 'location';
const ARTWORK = 'artwork';

function dateJson(field: DateField, today: string): Json {
	const { date } = toUncertainDate(field, today);
	return date as unknown as Json;
}

function sourceOperations(form: ArtworkForm): Json[] {
	return form.sources.map((source): Json => ({
		op: 'create',
		ref: source.key,
		kind: 'source',
		record: {
			title: text(source.title),
			author: text(source.author),
			publication: text(source.publication),
			url: text(source.url),
			note: text(source.note)
		}
	}));
}

function documentationOperations(form: ArtworkForm, today: string, about: Json): Json[] {
	return form.documentation.map((item): Json => {
		const common = { observed_date: dateJson(item.observed, today), artworks: [about] };
		return {
			op: 'create',
			ref: item.key,
			kind: 'documentation_item',
			record:
				item.medium === 'link'
					? { medium: 'link', ...common, url: text(item.url) }
					: {
							medium: item.medium,
							...common,
							file: item.file,
							licence: text(item.licence),
							creator_credit: text(item.creatorCredit),
							rights_basis: item.rightsBasis || null,
							origin_url: item.rightsBasis === 'third_party' ? text(item.originUrl) : null,
							...(item.medium === 'image' ? { alt_text: text(item.altText) } : {})
						}
		};
	});
}

const EVENT = 'event';

/** What the editor keeps beside the operations, to resume where it was left. */
function filesPart(form: ArtworkForm): Dict {
	return {
		counter: form.counter,
		files: Object.fromEntries(
			form.documentation.flatMap((each) => (each.file ? [[each.file, each.fileName]] : []))
		),
		suggested: form.documentation.filter((each) => each.suggested).map((each) => each.key)
	};
}

/**
 * The working copy for an Artwork that exists: its new Documentation items and Sources, and
 * a History event that cites them (or, with no event, the Sources as the Artwork's own).
 */
function toAttachedCopy(form: ArtworkForm, today: string, flavour: Flavour): Dict {
	const target = form.target;
	const about: Json = target?.id ?? null;
	const operations: Json[] = [
		...sourceOperations(form),
		...documentationOperations(form, today, about)
	];
	const { event } = form;
	const cited = [...form.sources, ...form.documentation].map((each) => ref(each.key));
	if (flavour === 'event' || event.shows === true) {
		operations.push({
			op: 'add',
			target: about,
			collection: 'history_events',
			item: {
				id: ref(EVENT),
				type: event.type || null,
				observed_date: dateJson(event.observed, today),
				condition: event.type === 'condition_recorded' ? event.condition || null : null,
				note: text(event.note),
				citations: cited,
				covering: event.type === 'covered' ? (event.covering?.id ?? null) : null
			}
		});
	} else {
		for (const source of form.sources) {
			operations.push({ op: 'add', target: about, collection: 'sources', item: ref(source.key) });
		}
	}
	return {
		operations,
		initial_condition: null,
		editor: {
			...filesPart(form),
			flavour,
			target,
			event: {
				shows: event.shows,
				type: event.type,
				observed: event.observed as unknown as Json,
				condition: event.condition,
				note: event.note,
				covering: event.covering,
				report: event.report
			}
		}
	};
}

/** The working copy of the form, as the API stores it (never validated on save). */
export function toWorkingCopy(form: ArtworkForm, today: string, flavour: Flavour = 'new'): Dict {
	if (flavour !== 'new') return toAttachedCopy(form, today, flavour);
	const operations: Json[] = [];
	const { location } = form;

	if (!location.existing && location.geometry) {
		operations.push({
			op: 'create',
			ref: LOCATION,
			kind: 'location',
			record: {
				geometry: location.geometry as unknown as Json,
				surface_type: text(location.surfaceType),
				approximate: location.approximate,
				uncertainty_radius: location.radius,
				place_description: text(location.placeDescription)
			}
		});
	}

	// Unknown authorship, said explicitly, has no Attribution, whatever was entered before.
	const attributions = form.attributed ? form.attributions : [];
	const newArtists = attributions.flatMap((each) =>
		each.artist?.kind === 'new' ? [each.artist] : []
	);
	for (const artist of newArtists) {
		operations.push({
			op: 'create',
			ref: artist.key,
			kind: 'artist',
			record: { name: text(artist.name), kind: artist.artistKind }
		});
	}
	for (const series of form.series.filter((each) => each.key !== null)) {
		operations.push({
			op: 'create',
			ref: series.key,
			kind: 'series',
			record: { name: text(series.name) }
		});
	}
	operations.push(...sourceOperations(form), ...documentationOperations(form, today, ref(ARTWORK)));

	const created = dateJson(form.created.date, today);
	operations.push({
		op: 'create',
		ref: ARTWORK,
		kind: 'artwork',
		record: {
			location: location.existing ? location.existing.id : location.geometry ? ref(LOCATION) : null,
			expression_types: form.expressionTypes,
			title: form.untitled ? null : text(form.title),
			description: text(form.description),
			attributions: attributions.map((each): Json => ({
				artist: each.artist
					? each.artist.kind === 'existing'
						? each.artist.id
						: ref(each.artist.key)
					: null,
				certainty: each.certainty || null,
				alias: text(each.alias),
				note: text(each.note),
				citations: each.citations.map(ref)
			})),
			history_events:
				created === null
					? []
					: [
							{
								id: ref('created'),
								type: 'created',
								observed_date: created,
								citations: form.created.citations.map(ref)
							}
						],
			series: form.series.map((each) => (each.id !== null ? each.id : ref(each.key ?? ''))),
			sources: form.sources.map((each) => ref(each.key))
		}
	});

	const labels: Dict = {};
	if (location.existing) labels[`location:${location.existing.id}`] = location.existing.title;
	for (const each of attributions) {
		if (each.artist?.kind === 'existing') labels[`artist:${each.artist.id}`] = each.artist.name;
	}
	for (const each of form.series) if (each.id !== null) labels[`series:${each.id}`] = each.name;

	return {
		operations,
		initial_condition: form.initialCondition || null,
		editor: {
			untitled: form.untitled,
			attributed: form.attributed,
			confirmed_key: location.confirmedKey,
			counter: form.counter,
			labels,
			files: Object.fromEntries(
				form.documentation.flatMap((each) => (each.file ? [[each.file, each.fileName]] : []))
			),
			suggested: form.documentation.filter((each) => each.suggested).map((each) => each.key)
		}
	};
}

function isDict(value: unknown): value is Dict {
	return typeof value === 'object' && value !== null && !Array.isArray(value);
}

const str = (value: unknown): string => (typeof value === 'string' ? value : '');
const strings = (value: unknown): string[] =>
	Array.isArray(value) ? value.filter((each): each is string => typeof each === 'string') : [];
const keyOf = (value: unknown): string | null =>
	isDict(value) && typeof value.new === 'string' ? value.new : null;

function dateOf(value: unknown): DateField {
	return isDict(value) && typeof value.precision === 'string'
		? fromUncertainDate(value as unknown as UncertainDate)
		: emptyDate();
}

/**
 * The form of a stored working copy. A copy that holds nothing (a draft just started),
 * or that this editor did not write, gives the empty form: nothing is ever refused here.
 */
export function fromWorkingCopy(copy: unknown): ArtworkForm {
	const form = emptyForm();
	if (!isDict(copy) || !Array.isArray(copy.operations)) return form;
	// A round's snapshot has no `editor` part: it was validated when submitted, so what it
	// leaves out is read from the changeset (a null title is *Untitled*, and so on).
	const fromRound = !isDict(copy.editor);
	const editor = isDict(copy.editor) ? copy.editor : {};
	const labels = isDict(editor.labels) ? editor.labels : {};
	const files = isDict(editor.files) ? editor.files : {};
	const suggested = strings(editor.suggested);
	form.counter = typeof editor.counter === 'number' ? editor.counter : 0;
	form.untitled = editor.untitled === true;
	form.attributed = typeof editor.attributed === 'boolean' ? editor.attributed : null;
	form.location.confirmedKey =
		typeof editor.confirmed_key === 'string' ? editor.confirmed_key : null;
	const condition = copy.initial_condition;
	if (typeof condition === 'string') form.initialCondition = condition as Condition;

	const creates = copy.operations.filter(isDict).filter((each) => each.op === 'create');
	const records = new Map<string, Dict>();
	for (const each of creates) {
		if (typeof each.ref === 'string' && isDict(each.record)) {
			records.set(`${str(each.kind)}:${each.ref}`, each.record);
		}
	}
	const label = (kind: string, id: unknown) => str(labels[`${kind}:${id}`]);

	const artwork = records.get(`artwork:${ARTWORK}`);
	const location = records.get(`location:${LOCATION}`);
	if (location) {
		form.location.geometry = (location.geometry ?? null) as unknown as Geometry | null;
		form.location.approximate = location.approximate === true;
		form.location.radius =
			typeof location.uncertainty_radius === 'number' ? location.uncertainty_radius : null;
		form.location.surfaceType = str(location.surface_type);
		form.location.placeDescription = str(location.place_description);
	}
	if (artwork) {
		if (typeof artwork.location === 'number') {
			form.location.existing = {
				id: artwork.location,
				title: label('location', artwork.location)
			};
		}
		form.title = str(artwork.title);
		form.untitled = fromRound ? artwork.title === null : form.untitled;
		form.description = str(artwork.description);
		form.expressionTypes = strings(artwork.expression_types);
		form.series = (Array.isArray(artwork.series) ? artwork.series : []).map((each) => {
			const key = keyOf(each);
			return key !== null
				? { id: null, key, name: str(records.get(`series:${key}`)?.name) }
				: { id: Number(each), key: null, name: label('series', each) };
		});
		form.attributions = (Array.isArray(artwork.attributions) ? artwork.attributions : [])
			.filter(isDict)
			.map((each): AttributionForm => {
				const key = keyOf(each.artist);
				const artist = records.get(`artist:${key}`);
				return {
					key: nextKey(form, 'attribution'),
					artist:
						key !== null
							? {
									kind: 'new',
									key,
									name: str(artist?.name),
									artistKind: artist?.kind === 'collective' ? 'collective' : 'individual'
								}
							: typeof each.artist === 'number'
								? { kind: 'existing', id: each.artist, name: label('artist', each.artist) }
								: null,
					certainty: ['confirmed', 'probable', 'disputed'].includes(str(each.certainty))
						? (each.certainty as Certainty)
						: '',
					alias: str(each.alias),
					note: str(each.note),
					citations: (Array.isArray(each.citations) ? each.citations : [])
						.map(keyOf)
						.filter((each): each is string => each !== null)
				};
			});
		if (fromRound) {
			form.attributed = form.attributions.length > 0;
			form.location.confirmedKey = placementKey(form.location);
		}
		const events = Array.isArray(artwork.history_events)
			? artwork.history_events.filter(isDict)
			: [];
		const creation = events.find((each) => each.type === 'created');
		if (creation) {
			form.created = {
				date: dateOf(creation.observed_date),
				citations: (Array.isArray(creation.citations) ? creation.citations : [])
					.map(keyOf)
					.filter((each): each is string => each !== null)
			};
		}
	}
	for (const [id, record] of records) {
		const [kind, key] = id.split(/:(.*)/s);
		if (kind === 'source') {
			form.sources.push({
				key,
				title: str(record.title),
				author: str(record.author),
				publication: str(record.publication),
				url: str(record.url),
				note: str(record.note)
			});
		} else if (kind === 'documentation_item') {
			const medium: DocMedium =
				record.medium === 'link' ? 'link' : record.medium === 'pdf' ? 'pdf' : 'image';
			const file = typeof record.file === 'string' ? record.file : null;
			form.documentation.push({
				key,
				medium,
				file,
				fileName: file ? str(files[file]) : '',
				observed: dateOf(record.observed_date),
				suggested: suggested.includes(key),
				rightsBasis:
					record.rights_basis === 'third_party'
						? 'third_party'
						: record.rights_basis === 'own_work'
							? 'own_work'
							: '',
				creatorCredit: str(record.creator_credit),
				licence: str(record.licence),
				originUrl: str(record.origin_url),
				altText: str(record.alt_text),
				url: str(record.url)
			});
		}
	}
	attachedFrom(copy.operations.filter(isDict), editor, form);
	return form;
}

/** The Artwork a copy is about and its History event, for the two flavours that attach. */
function attachedFrom(operations: Dict[], editor: Dict, form: ArtworkForm): void {
	const saved = isDict(editor.target) ? editor.target : null;
	const added = operations.find(
		(each) => each.op === 'add' && each.collection === 'history_events'
	);
	const aboutDocumentation = operations.find((each) => each.kind === 'documentation_item');
	const about =
		typeof saved?.id === 'number'
			? saved.id
			: typeof operations.find((each) => typeof each.target === 'number')?.target === 'number'
				? (operations.find((each) => typeof each.target === 'number')!.target as number)
				: isDict(aboutDocumentation?.record) &&
					  Array.isArray(aboutDocumentation.record.artworks) &&
					  typeof aboutDocumentation.record.artworks[0] === 'number'
					? aboutDocumentation.record.artworks[0]
					: null;
	if (about !== null) form.target = { id: about, title: saved ? str(saved.title) : '' };

	const kept = isDict(editor.event) ? editor.event : {};
	const item = isDict(added?.item) ? added.item : null;
	form.event = {
		shows: typeof kept.shows === 'boolean' ? kept.shows : item ? true : null,
		type: (str(kept.type) || str(item?.type)) as EventForm['type'],
		observed: isDict(kept.observed)
			? (kept.observed as unknown as DateField)
			: dateOf(item?.observed_date),
		condition: (str(kept.condition) || str(item?.condition)) as EventForm['condition'],
		note: typeof kept.note === 'string' ? kept.note : str(item?.note),
		covering:
			isDict(kept.covering) && typeof kept.covering.id === 'number'
				? { id: kept.covering.id, title: str(kept.covering.title) }
				: typeof item?.covering === 'number'
					? { id: item.covering, title: '' }
					: null,
		report: kept.report === true
	};
}

/**
 * Which editor an edit of an Artwork needs, from the copy the Submitter works on or the
 * last round: the editor names it; a round, which has no editor part, is read from what it
 * does (new Documentation items: documentation; only a History event: event).
 */
export function artworkEditorOf(copy: unknown): 'edit' | 'documentation' | 'event' {
	if (!isDict(copy) || !Array.isArray(copy.operations)) return 'edit';
	const named = isDict(copy.editor) ? copy.editor.flavour : null;
	if (named === 'documentation' || named === 'event' || named === 'edit') return named;
	const operations = copy.operations.filter(isDict);
	if (operations.some((each) => each.op === 'create' && each.kind === 'documentation_item')) {
		return 'documentation';
	}
	const edits = operations.filter((each) => each.op !== 'create');
	return edits.length > 0 && edits.every((each) => each.collection === 'history_events')
		? 'event'
		: 'edit';
}
