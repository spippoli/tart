import { describe, expect, it } from 'vitest';
import { indexQueryString, readIndexQuery } from './index-query';

// The unit tests run in the base locale, Italian.
describe('the index query string', () => {
	it('reads the localized keys, and the other language keys too', () => {
		expect(readIndexQuery(new URLSearchParams('nome=lupo&pagina=3'))).toEqual({
			name: 'lupo',
			page: 3
		});
		expect(readIndexQuery(new URLSearchParams('name=lupo&page=3'))).toEqual({
			name: 'lupo',
			page: 3
		});
	});

	it('takes an absent, malformed, or first page as page 1, and a blank name as none', () => {
		expect(readIndexQuery(new URLSearchParams(''))).toEqual({ name: null, page: 1 });
		for (const value of ['0', '1', '-4', 'x', '2.5']) {
			expect(readIndexQuery(new URLSearchParams({ pagina: value })).page).toBe(1);
		}
		expect(readIndexQuery(new URLSearchParams({ nome: '   ' })).name).toBeNull();
	});

	it('writes the keys of the UI language and omits the defaults', () => {
		expect(indexQueryString({ page: 1, name: null })).toBe('');
		expect(indexQueryString({ page: 2, name: null })).toBe('?pagina=2');
		expect(indexQueryString({ page: 1, name: 'città vuota' })).toBe('?nome=citt%C3%A0+vuota');
	});
});
