import { error, redirect, type RequestEvent } from '@sveltejs/kit';
import { readIndexQuery } from '#lib/archive/index-query.ts';
import { API_SEGMENTS, ROUTES, type Kind } from '#lib/archive/records.ts';
import { localizeHref } from '#lib/paraglide/runtime.js';
import { api, onBehalfOf } from './api';

/**
 * Loading a record page (archive-records spec, Public record pages): only the id in
 * `{id}-{slug}` resolves the record; any other path than the canonical one (a wrong,
 * missing, or outdated slug, or a merged duplicate's id, which the API redirects to
 * its survivor) answers 301. The API's 404 and 410 become the page's.
 */

const REF = /^(\d+)(?:-.*)?$/;

type Fetched<T> = { data?: T; response: Response };

export async function fetchView<T>(event: RequestEvent, path: string): Promise<Fetched<T>> {
	// The archive routes are many and alike; they are typed by the caller's `T`.
	const get = api().GET as unknown as (
		path: string,
		init: { headers: Record<string, string> }
	) => Promise<Fetched<T>>;
	return get(path, { headers: onBehalfOf(event) });
}

function recordId(ref: string): number {
	const found = REF.exec(ref);
	if (!found) error(404);
	return Number(found[1]);
}

function failOn(response: Response): never {
	if (response.status === 404 || response.status === 410) error(response.status);
	throw new Error(`the API answered ${response.status}`);
}

export interface Vocabularies {
	expressionTypes: { key: string; label: Record<string, string> }[];
	surfaceTypes: { key: string; label: Record<string, string> }[];
}

export function vocabularies(event: RequestEvent): Vocabularies {
	const { vocabularies } = event.locals.config;
	return {
		expressionTypes: vocabularies.expression_types,
		surfaceTypes: vocabularies.surface_types
	};
}

/** The view of the record that `params.ref` names, at its canonical URL. */
export async function loadRecord<T extends { id: number; path: string }>(
	event: RequestEvent,
	kind: Kind
): Promise<T> {
	const ref = event.params.ref ?? '';
	const id = recordId(ref);
	const { data, response } = await fetchView<T>(event, `/api/archive/${API_SEGMENTS[kind]}/${id}`);
	if (!data) failOn(response);
	if (data.path !== ref) redirect(301, localizeHref(`${ROUTES[kind]}/${data.path}`));
	return data;
}

/** The Revisions of the record that `params.ref` names, at its canonical URL. */
export async function loadRevisions<T extends { record: { id: number; path: string } }>(
	event: RequestEvent,
	kind: Kind
): Promise<T> {
	const ref = event.params.ref ?? '';
	const id = recordId(ref);
	const { data, response } = await fetchView<T>(
		event,
		`/api/archive/${API_SEGMENTS[kind]}/${id}/revisions`
	);
	if (!data) failOn(response);
	if (data.record.path !== ref) {
		redirect(301, localizeHref(`${ROUTES[kind]}/${data.record.path}/revisions`));
	}
	return data;
}

/** A page of an index (Artists, Sites, Areas, Series). */
export async function loadIndex<T>(event: RequestEvent, kind: Kind): Promise<T> {
	const { page, name } = readIndexQuery(event.url.searchParams);
	const query = new URLSearchParams({ page: String(page), ...(name ? { name } : {}) });
	const { data, response } = await fetchView<T>(
		event,
		`/api/archive/${API_SEGMENTS[kind]}?${query}`
	);
	if (!data) failOn(response);
	return data;
}
