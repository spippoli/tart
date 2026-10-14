import { describe, expect, it } from 'vitest';
import {
	CONDITIONS,
	EMPTY_STATE,
	apiQuery,
	forOtherView,
	normaliseQuery,
	parseState,
	queryString,
	remapSearch,
	serialiseState,
	type FilterState
} from './state';

const parse = (search: string, locale: 'it' | 'en' = 'it') =>
	parseState(new URLSearchParams(search), locale);

// Discovery criterion 51: the keys, the values, repeatable keys, defaults, and unknown input.
describe('the query string (criterion 51)', () => {
	const everything: FilterState = {
		q: 'muro rosso',
		order: 'title',
		condition: ['covered', 'destroyed'],
		type: ['stencil', 'sticker'],
		area: [3, 4],
		attribution: ['unknown', 'disputed'],
		artist: 7,
		series: 6,
		documentedFrom: 2010,
		documentedTo: 2020,
		createdFrom: 2000,
		createdTo: 2012,
		location: 11,
		viewport: { zoom: 14, lat: 41.9, lon: 12.5 },
		page: 3
	};

	it('round-trips every key in each UI language', () => {
		for (const locale of ['it', 'en'] as const) {
			const text = serialiseState(everything, locale).toString();
			expect(parseState(new URLSearchParams(text), locale)).toEqual(everything);
		}
	});

	it('uses the localized keys of the spec', () => {
		const it = serialiseState(everything, 'it');
		expect([...new Set(it.keys())]).toEqual([
			'q',
			'ordine',
			'condizione',
			'tipo',
			'area',
			'attribuzione',
			'artista',
			'serie',
			'documentata-dal',
			'documentata-al',
			'creata-dal',
			'creata-al',
			'superficie',
			'mappa',
			'pagina'
		]);
		const en = serialiseState(everything, 'en');
		expect([...new Set(en.keys())]).toEqual([
			'q',
			'sort',
			'condition',
			'type',
			'area',
			'attribution',
			'artist',
			'series',
			'documented-from',
			'documented-to',
			'created-from',
			'created-to',
			'location',
			'map',
			'page'
		]);
	});

	it('repeats a repeatable key and keeps the values stable in both languages', () => {
		expect(queryString(everything, 'en')).toContain('type=stencil&type=sticker');
		expect(queryString(everything, 'it')).toContain('tipo=stencil&tipo=sticker');
		expect(queryString(everything, 'it')).toContain('attribuzione=unknown&attribuzione=disputed');
		expect(queryString(everything, 'it')).toContain('map');
	});

	it('omits defaults', () => {
		expect(queryString(EMPTY_STATE, 'it')).toBe('');
		expect(queryString({ ...EMPTY_STATE, page: 1, order: null }, 'en')).toBe('');
		expect(parse('ordine=recent').order).toBeNull();
		expect(parse('pagina=1').page).toBe(1);
	});

	it('ignores unknown keys and malformed values, and drops them from the canonical form', () => {
		const messy =
			'?foo=1&ordine=popolarita&condizione=sparito&area=abc&area=-3&documentata-dal=20x&superficie=0&mappa=x/y/z&pagina=-2';
		expect(parse(messy)).toEqual(EMPTY_STATE);
		expect(queryString(parse(messy), 'it')).toBe('');
		expect(parse('ordine=title&foo=bar').order).toBe('title');
		expect(queryString(parse('foo=bar&tipo=stencil'), 'it')).toBe('?tipo=stencil');
	});

	it('accepts a key of the other UI language', () => {
		expect(parse('type=mural&sort=oldest', 'it')).toMatchObject({
			type: ['mural'],
			order: 'oldest'
		});
		expect(parse('tipo=mural&ordine=oldest', 'en')).toMatchObject({
			type: ['mural'],
			order: 'oldest'
		});
	});

	it('ignores "relevance" without a search, and keeps a chosen order next to one', () => {
		expect(parse('ordine=relevance').order).toBeNull();
		expect(parse('q=muro&ordine=relevance').order).toBe('relevance');
		expect(parse('q=muro&ordine=recent').order).toBe('recent');
		expect(queryString(parse('q=muro&ordine=recent'), 'en')).toBe('?q=muro&sort=recent');
	});
});

// Criterion 35: remapping on a UI-language switch.
describe('the language switch (criterion 35)', () => {
	it('remaps the keys and leaves the values alone', () => {
		const italian = '?q=gatto&tipo=stencil&condizione=covered&creata-dal=2010&pagina=2';
		const english = remapSearch(italian, 'it', 'en');

		expect(english).toBe('?q=gatto&condition=covered&type=stencil&created-from=2010&page=2');
		expect(remapSearch(english, 'en', 'it')).toBe(
			'?q=gatto&condizione=covered&tipo=stencil&creata-dal=2010&pagina=2'
		);
	});

	it('never translates a value into a label', () => {
		const state = parse('condizione=destroyed&attribuzione=disputed&ordine=oldest');
		expect(queryString(state, 'en')).toBe('?sort=oldest&condition=destroyed&attribution=disputed');
	});
});

// Criterion 52: single Conditions only; no key means all nine.
describe('the Condition filter (criterion 52)', () => {
	it('holds single Conditions in the order of the vocabulary', () => {
		expect(parse('condizione=destroyed&condizione=intact').condition).toEqual([
			'intact',
			'destroyed'
		]);
	});

	it('removes the key when all nine are selected', () => {
		const all = CONDITIONS.map((condition) => `condizione=${condition}`).join('&');
		expect(parse(all).condition).toEqual([]);
		expect(queryString(parse(all), 'it')).toBe('');
	});

	it('does not know groups as values', () => {
		expect(parse('condizione=disappeared').condition).toEqual([]);
	});
});

describe('the query', () => {
	it('is trimmed, collapsed, absent under two characters, and cut at 100', () => {
		expect(normaliseQuery('  muro   rosso ')).toBe('muro rosso');
		expect(normaliseQuery('a')).toBeNull();
		expect(normaliseQuery(' a ')).toBeNull();
		expect(normaliseQuery('x'.repeat(150))).toHaveLength(100);
	});
});

describe('views', () => {
	it('keeps the filters and drops the viewport when switching views (criterion 17)', () => {
		const state = parse('tipo=stencil&mappa=14/41.9/12.5&superficie=3&pagina=2');
		expect(queryString(forOtherView(state), 'it')).toBe('?tipo=stencil');
	});

	it('speaks to the API in its own parameters', () => {
		const query = apiQuery(
			parse('q=gatto&tipo=stencil&documentata-dal=2010&pagina=2&mappa=14/41.9/12.5')
		);
		expect(query.toString()).toBe('q=gatto&type=stencil&documented_from=2010&page=2');
	});
});
