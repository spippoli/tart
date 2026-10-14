import { m } from '#lib/paraglide/messages.js';
import { getLocale, locales, type Locale } from '#lib/paraglide/runtime.js';

/**
 * The query string of the indexes (Discovery spec, Query-string keys): `?nome=` and
 * `?pagina=` in Italian, `?name=` and `?page=` in English. A key in another UI language
 * is accepted as well; an absent page is page 1, and a malformed value is ignored.
 */

type Key = (inputs: Record<string, never>, options: { locale: Locale }) => string;

/** The value of a key in any UI language, the current one first. */
function valueOf(params: { get(name: string): string | null }, key: Key): string | null {
	const current = getLocale();
	for (const locale of [current, ...locales.filter((other) => other !== current)]) {
		const found = params.get(key({}, { locale }));
		if (found !== null) return found;
	}
	return null;
}

export interface IndexQuery {
	page: number;
	/** The name to filter by, or `null`. */
	name: string | null;
}

export function readIndexQuery(params: { get(name: string): string | null }): IndexQuery {
	const page = Number(valueOf(params, m.query_key_page));
	const name = valueOf(params, m.query_key_name)?.trim();
	return { page: Number.isInteger(page) && page >= 2 ? page : 1, name: name || null };
}

/** The query string of a page of an index, in the current UI language; default values are omitted. */
export function indexQueryString({ page, name }: IndexQuery): string {
	const params = new URLSearchParams();
	if (name) params.set(m.query_key_name(), name);
	if (page >= 2) params.set(m.query_key_page(), String(page));
	const text = params.toString();
	return text ? `?${text}` : '';
}
