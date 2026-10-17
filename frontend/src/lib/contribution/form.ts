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
export type Step = (typeof STEPS)[number];

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

export interface ArtworkForm {
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

/** The working copy of the form, as the API stores it (never validated on save). */
export function toWorkingCopy(form: ArtworkForm, today: string): Dict {
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
	for (const source of form.sources) {
		operations.push({
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
		});
	}
	for (const item of form.documentation) {
		const common = { observed_date: dateJson(item.observed, today), artworks: [ref(ARTWORK)] };
		operations.push({
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
		});
	}

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
	return form;
}
