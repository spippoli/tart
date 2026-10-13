import { describe, expect, it } from 'vitest';
import { safeNext } from './next';

const ORIGIN = 'https://archive.example.org';

describe('the return page after sign-in', () => {
	it('keeps a path on this site, with its query', () => {
		expect(safeNext('/en/about?x=1#y', ORIGIN)).toBe('/en/about?x=1#y');
		expect(safeNext('/it/moderazione', ORIGIN)).toBe('/it/moderazione');
	});

	it.each([
		null,
		'',
		'https://evil.example/',
		'//evil.example/',
		'/\\evil.example',
		'javascript:alert(1)',
		'en/about',
		'/.//evil.example',
		'/..//evil.example',
		'/a/..//evil.example',
		'/%2e//evil.example',
		'/.\t//evil.example'
	])('refuses %s', (value) => {
		expect(safeNext(value, ORIGIN)).toBeNull();
	});
});
