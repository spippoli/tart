/**
 * The filter state (Discovery spec, Modules and Query-string keys): search, filters,
 * order, selection, viewport, and page, read from and written to the query string.
 * Keys are UI strings per language; values are always stable (vocabulary keys, ids,
 * enum values). Unknown keys and malformed values are ignored, never an error.
 */
import { m } from '#lib/paraglide/messages.js';
import { locales, type Locale } from '#lib/paraglide/runtime.js';
import type { Condition, ConditionGroup } from '#lib/archive/records.ts';

export type Order = 'recent' | 'oldest' | 'added' | 'title' | 'relevance';
export type AttributionFilter = 'unknown' | 'attributed' | 'disputed';

export const ORDERS: readonly Order[] = ['recent', 'oldest', 'added', 'title', 'relevance'];
export const ATTRIBUTIONS: readonly AttributionFilter[] = ['unknown', 'attributed', 'disputed'];

/** The nine Conditions, by Condition group (ADR 0015), in the order they are shown. */
export const CONDITION_GROUPS: readonly { group: ConditionGroup; conditions: Condition[] }[] = [
	{ group: 'present', conditions: ['intact', 'deteriorated', 'damaged', 'modified'] },
	{ group: 'disappeared', conditions: ['covered', 'removed', 'destroyed', 'missing'] },
	{ group: 'unknown', conditions: ['unknown'] }
];
export const CONDITIONS: readonly Condition[] = CONDITION_GROUPS.flatMap((g) => g.conditions);

export const PAGE_SIZE = 24;
export const MAX_QUERY_LENGTH = 100;

export interface Viewport {
	zoom: number;
	lat: number;
	lon: number;
}

export interface FilterState {
	q: string | null;
	/** Only a choice that differs from the default of the view. */
	order: Order | null;
	/** Single Conditions; empty means all nine. */
	condition: Condition[];
	type: string[];
	area: number[];
	attribution: AttributionFilter[];
	artist: number | null;
	series: number | null;
	documentedFrom: number | null;
	documentedTo: number | null;
	createdFrom: number | null;
	createdTo: number | null;
	/** The selected Location. */
	location: number | null;
	viewport: Viewport | null;
	/** 1 when absent. */
	page: number;
}

export const EMPTY_STATE: FilterState = {
	q: null,
	order: null,
	condition: [],
	type: [],
	area: [],
	attribution: [],
	artist: null,
	series: null,
	documentedFrom: null,
	documentedTo: null,
	createdFrom: null,
	createdTo: null,
	location: null,
	viewport: null,
	page: 1
};

type Message = (inputs: Record<string, never>, options: { locale: Locale }) => string;

/** Each concept's key in each UI language; `q` is the same in all of them. */
const KEYS = {
	order: m.discovery_key_order,
	condition: m.discovery_key_condition,
	type: m.discovery_key_type,
	area: m.discovery_key_area,
	attribution: m.discovery_key_attribution,
	artist: m.discovery_key_artist,
	series: m.discovery_key_series,
	documentedFrom: m.discovery_key_documented_from,
	documentedTo: m.discovery_key_documented_to,
	createdFrom: m.discovery_key_created_from,
	createdTo: m.discovery_key_created_to,
	location: m.discovery_key_location,
	viewport: m.discovery_key_viewport,
	page: m.discovery_key_page,
	name: m.discovery_key_name
} satisfies Record<string, Message>;

export type Concept = keyof typeof KEYS | 'q';

/** The query-string key of a concept in a UI language. */
export function queryKey(concept: Concept, locale: Locale): string {
	return concept === 'q' ? 'q' : KEYS[concept]({}, { locale });
}

/** Every value of a concept's key, in the `locale` key if it is there, else in any other UI language's. */
function values(params: URLSearchParams, concept: Concept, locale: Locale): string[] {
	const order = [locale, ...locales.filter((other) => other !== locale)];
	for (const language of order) {
		const found = params.getAll(queryKey(concept, language));
		if (found.length > 0) return found;
	}
	return [];
}

function first(params: URLSearchParams, concept: Concept, locale: Locale): string | undefined {
	return values(params, concept, locale)[0];
}

function integer(text: string | undefined, min: number, max: number): number | null {
	if (text === undefined || !/^\d+$/.test(text.trim())) return null;
	const value = Number(text);
	return value >= min && value <= max ? value : null;
}

const unique = <T>(items: T[]): T[] => [...new Set(items)];

/** `q` as the API reads it: trimmed, whitespace collapsed, under 2 characters absent, cut at 100. */
export function normaliseQuery(text: string | null | undefined): string | null {
	const collapsed = (text ?? '').replace(/\s+/g, ' ').trim().slice(0, MAX_QUERY_LENGTH).trim();
	return collapsed.length >= 2 ? collapsed : null;
}

function viewport(text: string | undefined): Viewport | null {
	const found = /^(\d{1,2}(?:\.\d+)?)\/(-?\d{1,2}(?:\.\d+)?)\/(-?\d{1,3}(?:\.\d+)?)$/.exec(
		text ?? ''
	);
	if (!found) return null;
	const [zoom, lat, lon] = [Number(found[1]), Number(found[2]), Number(found[3])];
	return zoom <= 24 && Math.abs(lat) <= 90 && Math.abs(lon) <= 180 ? { zoom, lat, lon } : null;
}

const MAX_ID = Number.MAX_SAFE_INTEGER;

/** The state a query string holds; the keys of any UI language are accepted. */
export function parseState(params: URLSearchParams, locale: Locale): FilterState {
	const q = normaliseQuery(first(params, 'q', locale));
	const order = values(params, 'order', locale).find((value): value is Order =>
		(ORDERS as readonly string[]).includes(value)
	);
	const conditions = unique(
		values(params, 'condition', locale).filter((value): value is Condition =>
			(CONDITIONS as readonly string[]).includes(value)
		)
	);
	const attributions = values(params, 'attribution', locale);
	return {
		q,
		// "Relevance" exists only with a search, and "recent" is the default without one.
		order: !order || (!q && (order === 'relevance' || order === 'recent')) ? null : order,
		condition:
			conditions.length === CONDITIONS.length
				? []
				: CONDITIONS.filter((condition) => conditions.includes(condition)),
		type: unique(values(params, 'type', locale).filter((value) => value !== '')),
		area: unique(
			values(params, 'area', locale)
				.map((value) => integer(value, 1, MAX_ID))
				.filter((value): value is number => value !== null)
		),
		attribution: ATTRIBUTIONS.filter((value) => attributions.includes(value)),
		artist: integer(first(params, 'artist', locale), 1, MAX_ID),
		series: integer(first(params, 'series', locale), 1, MAX_ID),
		documentedFrom: integer(first(params, 'documentedFrom', locale), 1, 9999),
		documentedTo: integer(first(params, 'documentedTo', locale), 1, 9999),
		createdFrom: integer(first(params, 'createdFrom', locale), 1, 9999),
		createdTo: integer(first(params, 'createdTo', locale), 1, 9999),
		location: integer(first(params, 'location', locale), 1, MAX_ID),
		viewport: viewport(first(params, 'viewport', locale)),
		page: integer(first(params, 'page', locale), 2, 1_000_000) ?? 1
	};
}

/** The canonical query string of a state in a UI language: defaults omitted, repeatable keys repeated. */
export function serialiseState(state: FilterState, locale: Locale): URLSearchParams {
	const params = new URLSearchParams();
	const set = (concept: Concept, value: string | number | null) => {
		if (value !== null) params.append(queryKey(concept, locale), String(value));
	};
	const many = (concept: Concept, list: readonly (string | number)[]) =>
		list.forEach((value) => set(concept, value));
	set('q', state.q);
	set('order', state.order);
	if (state.condition.length < CONDITIONS.length) many('condition', state.condition);
	many('type', state.type);
	many('area', state.area);
	many('attribution', state.attribution);
	set('artist', state.artist);
	set('series', state.series);
	set('documentedFrom', state.documentedFrom);
	set('documentedTo', state.documentedTo);
	set('createdFrom', state.createdFrom);
	set('createdTo', state.createdTo);
	set('location', state.location);
	if (state.viewport) {
		const { zoom, lat, lon } = state.viewport;
		set('viewport', `${zoom}/${lat}/${lon}`);
	}
	if (state.page > 1) set('page', state.page);
	return params;
}

/** The query string, with the keys of `locale`, as `?…` or an empty string. */
export function queryString(state: FilterState, locale: Locale): string {
	const text = serialiseState(state, locale).toString();
	return text ? `?${text}` : '';
}

/** A query string of one UI language rewritten for another (the language switcher). */
export function remapSearch(search: string, from: Locale, to: Locale): string {
	return queryString(parseState(new URLSearchParams(search), from), to);
}

/** Switching views keeps the filters and drops the viewport, the selection, and the page. */
export function forOtherView(state: FilterState): FilterState {
	return { ...state, viewport: null, location: null, page: 1 };
}

/** How many filters narrow the results (order, selection, viewport, and page do not). */
export function filterCount(state: FilterState): number {
	return [
		state.q,
		state.condition.length > 0,
		state.type.length > 0,
		state.area.length > 0,
		state.attribution.length > 0,
		state.artist !== null,
		state.series !== null,
		state.documentedFrom !== null || state.documentedTo !== null,
		state.createdFrom !== null || state.createdTo !== null
	].filter(Boolean).length;
}

/** The API's query for a state, in its own parameter names. */
export function apiQuery(state: FilterState): URLSearchParams {
	const params = new URLSearchParams();
	const set = (name: string, value: string | number | null) => {
		if (value !== null) params.append(name, String(value));
	};
	set('q', state.q);
	set('order', state.order);
	state.condition.forEach((value) => set('condition', value));
	state.type.forEach((value) => set('type', value));
	state.area.forEach((value) => set('area', value));
	state.attribution.forEach((value) => set('attribution', value));
	set('artist', state.artist);
	set('series', state.series);
	set('documented_from', state.documentedFrom);
	set('documented_to', state.documentedTo);
	set('created_from', state.createdFrom);
	set('created_to', state.createdTo);
	if (state.page > 1) set('page', state.page);
	return params;
}
