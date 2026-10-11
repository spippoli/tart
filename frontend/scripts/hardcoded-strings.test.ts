import { readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { parse } from 'svelte/compiler';
import { describe, expect, it } from 'vitest';

/**
 * Foundations criterion 32: no user-facing string is hardcoded in a component.
 * Every text node with a letter, and every static value of an attribute that
 * people read or hear, must come from an expression (a message, or data).
 */
const ATTRIBUTES = new Set(['alt', 'title', 'placeholder', 'aria-label', 'aria-description']);
const LETTER = /\p{L}/u;

const root = path.resolve(import.meta.dirname, '../src');

function components(directory: string): string[] {
	return readdirSync(directory, { recursive: true, withFileTypes: true })
		.filter((entry) => entry.isFile() && entry.name.endsWith('.svelte'))
		.map((entry) => path.join(entry.parentPath, entry.name));
}

type Node = { type: string; [key: string]: unknown };

function hardcodedStrings(source: string): string[] {
	const ast = parse(source, { modern: true });
	const found: string[] = [];
	const visit = (node: unknown): void => {
		if (Array.isArray(node)) return node.forEach(visit);
		if (node === null || typeof node !== 'object') return;
		const current = node as Node;
		if (current.type === 'Text' && LETTER.test(String(current.data))) {
			found.push(String(current.data).trim());
		}
		if (current.type === 'Attribute') {
			// Other attributes (class, href, type, ...) are not read by people.
			const value = current.value;
			const hasText = Array.isArray(value) && value.some((part: Node) => part.type === 'Text');
			if (ATTRIBUTES.has(String(current.name)) && hasText) {
				found.push(`${current.name}="${value.map((part: Node) => part.data ?? '{…}').join('')}"`);
			}
			return;
		}
		for (const [key, child] of Object.entries(current)) {
			// Scripts and styles are code, not markup.
			if (key !== 'instance' && key !== 'module' && key !== 'css') visit(child);
		}
	};
	visit(ast.fragment);
	return found;
}

describe('AC 32: no hardcoded user-facing strings', () => {
	it('finds a hardcoded string', () => {
		expect(hardcodedStrings('<button aria-label="Chiudi">Chiudi</button>')).toEqual([
			'aria-label="Chiudi"',
			'Chiudi'
		]);
		expect(hardcodedStrings('<p>{m.x()} – {y}</p><img alt={m.a()} src="x.svg" />')).toEqual([]);
	});

	for (const file of components(root)) {
		it(`in ${path.relative(root, file)}`, () => {
			expect(hardcodedStrings(readFileSync(file, 'utf8'))).toEqual([]);
		});
	}
});
