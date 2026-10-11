import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { build } from 'vite';
import { describe, expect, it } from 'vitest';
import { findMissingKeys, messageKeysCheck } from './messages.ts';

function project(catalogues: Record<string, Record<string, string>>): string {
	const root = mkdtempSync(path.join(tmpdir(), 'tart-messages-'));
	const projectDir = path.join(root, 'project.inlang');
	mkdirSync(projectDir);
	mkdirSync(path.join(root, 'messages'));
	writeFileSync(
		path.join(projectDir, 'settings.json'),
		JSON.stringify({
			baseLocale: 'it',
			locales: Object.keys(catalogues),
			'plugin.inlang.messageFormat': { pathPattern: './messages/{locale}.json' }
		})
	);
	for (const [locale, messages] of Object.entries(catalogues)) {
		writeFileSync(
			path.join(root, 'messages', `${locale}.json`),
			JSON.stringify({ $schema: 'https://inlang.com/schema/inlang-message-format', ...messages })
		);
	}
	return projectDir;
}

describe('the message catalogue check', () => {
	it('passes on the shipped catalogues', () => {
		expect(findMissingKeys(path.resolve('project.inlang'))).toEqual([]);
	});

	it('passes when every locale has the same keys', () => {
		const dir = project({ it: { greeting: 'Ciao' }, en: { greeting: 'Hello' } });

		expect(findMissingKeys(dir)).toEqual([]);
	});

	it('reports a key missing from any locale, the default one included', () => {
		const dir = project({
			it: { greeting: 'Ciao', only_it: 'Solo' },
			en: { greeting: 'Hello', only_en: 'Only' }
		});

		expect(findMissingKeys(dir)).toEqual([
			{ locale: 'it', key: 'only_en' },
			{ locale: 'en', key: 'only_it' }
		]);
	});

	it('fails the build on a missing key', async () => {
		const dir = project({ it: { greeting: 'Ciao' }, en: {} });
		const entry = path.join(path.dirname(dir), 'entry.js');
		writeFileSync(entry, 'export {};\n');

		await expect(
			build({
				configFile: false,
				logLevel: 'silent',
				root: path.dirname(dir),
				plugins: [messageKeysCheck(dir)],
				build: { write: false, lib: { entry, formats: ['es'] } }
			})
		).rejects.toThrow(/en: greeting/);
	});
});
