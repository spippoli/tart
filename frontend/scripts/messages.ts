/**
 * Missing-key check for the Paraglide message catalogues (ADR 0008).
 *
 * Every UI language ships complete: a key present in one catalogue must be
 * present in all of them. The Vite plugin below fails `vite build` (and the
 * dev server) on a missing key; a unit test runs the same check in CI.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import type { Plugin } from 'vite';

export interface MissingKey {
	locale: string;
	key: string;
}

interface ProjectSettings {
	locales: string[];
	'plugin.inlang.messageFormat': { pathPattern: string };
}

function readJson(file: string): unknown {
	return JSON.parse(readFileSync(file, 'utf8'));
}

function messageKeys(file: string): Set<string> {
	const catalogue = readJson(file) as Record<string, unknown>;
	return new Set(Object.keys(catalogue).filter((key) => key !== '$schema'));
}

/** Lists, per locale, the keys that another locale's catalogue has and this one lacks. */
export function findMissingKeys(projectDir: string): MissingKey[] {
	const settings = readJson(path.join(projectDir, 'settings.json')) as ProjectSettings;
	// Paths in the settings are relative to the folder that holds the project.
	const root = path.dirname(projectDir);
	const pattern = settings['plugin.inlang.messageFormat'].pathPattern;
	const keysByLocale = new Map(
		settings.locales.map((locale) => [
			locale,
			messageKeys(path.resolve(root, pattern.replace('{locale}', locale)))
		])
	);
	const allKeys = new Set([...keysByLocale.values()].flatMap((keys) => [...keys]));
	const missing: MissingKey[] = [];
	for (const [locale, keys] of keysByLocale) {
		for (const key of [...allKeys].sort()) {
			if (!keys.has(key)) missing.push({ locale, key });
		}
	}
	return missing;
}

export function formatMissingKeys(missing: MissingKey[]): string {
	return ['Missing message keys:', ...missing.map(({ locale, key }) => `  ${locale}: ${key}`)].join(
		'\n'
	);
}

/** Fails the build when a catalogue lacks a key. */
export function messageKeysCheck(projectDir: string): Plugin {
	return {
		name: 'tart:message-keys-check',
		buildStart() {
			const missing = findMissingKeys(projectDir);
			if (missing.length > 0) this.error(formatMissingKeys(missing));
		}
	};
}
