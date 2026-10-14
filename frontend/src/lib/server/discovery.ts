import { redirect, type RequestEvent } from '@sveltejs/kit';
import type { components } from '../api/schema';
import { apiQuery, filterCount, PAGE_SIZE, parseState, queryString } from '#lib/discovery/state.ts';
import type { RecordLink } from '#lib/archive/records.ts';
import { getLocale } from '#lib/paraglide/runtime.js';
import { fetchView, vocabularies } from './records';

export type ArtworkPage = components['schemas']['ArtworkPage'];

/**
 * What the Explore and Archive views share (Discovery spec, Explore and Archive views):
 * the filter state of the query string, the page of matching Artworks that the
 * Discovery query returns, and what the filter form and its chips need to name.
 * A query string that is not the canonical one of its state (unknown keys, bad
 * values, defaults, a key of the other UI language) is answered with a redirect to
 * the canonical one, so the form works without JavaScript and shared URLs stay clean.
 */
export async function loadDiscovery(event: RequestEvent, view: 'explore' | 'archive') {
	const locale = getLocale();
	const parsed = parseState(event.url.searchParams, locale);
	// The Archive view ignores the viewport and keeps no selection.
	const state = view === 'archive' ? { ...parsed, viewport: null, location: null } : parsed;
	const canonical = queryString(state, locale);
	if (new URLSearchParams(event.url.search).toString() !== canonical.slice(1)) {
		redirect(303, event.url.pathname + canonical);
	}

	const { data, response } = await fetchView<ArtworkPage>(
		event,
		`/api/discovery/artworks?${apiQuery(state)}`
	);
	if (!data) throw new Error(`the API answered ${response.status}`);
	const pages = Math.max(1, Math.ceil(data.total / data.page_size));
	if (state.page > pages) {
		redirect(303, event.url.pathname + queryString({ ...state, page: pages }, locale));
	}

	return {
		state,
		results: data,
		pageSize: PAGE_SIZE,
		// A filtered or searched view with no results is not an empty archive.
		emptyArchive: data.total === 0 && filterCount(state) === 0,
		areas: await allAreas(event),
		linked: {
			artist: state.artist ? await nameOf(event, 'artists', state.artist) : null,
			series: state.series ? await nameOf(event, 'series', state.series) : null
		},
		...vocabularies(event)
	};
}

/** Every Area, for the Area filter. */
async function allAreas(event: RequestEvent): Promise<RecordLink[]> {
	const areas: RecordLink[] = [];
	for (let page = 1; ; page++) {
		const { data } = await fetchView<{ items: RecordLink[]; page_size: number; total: number }>(
			event,
			`/api/archive/areas?page=${page}`
		);
		if (!data) break;
		areas.push(...data.items);
		if (areas.length >= data.total || data.items.length === 0) break;
	}
	return areas;
}

/** The name of an Artist or Series, for its chip; none if it is not public. */
async function nameOf(
	event: RequestEvent,
	segment: 'artists' | 'series',
	id: number
): Promise<string | null> {
	const { data } = await fetchView<{ name: string | null }>(event, `/api/archive/${segment}/${id}`);
	return data?.name ?? null;
}

export type DiscoveryData = Awaited<ReturnType<typeof loadDiscovery>>;
