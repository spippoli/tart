/**
 * Third-party asset manifest check (ADR 0016 §1, §3).
 *
 *     node scripts/assets.ts    (pnpm check:assets)
 *
 * `third-party-assets.json` lists the third-party asset directories of the
 * repository and one entry per vendored asset (a file, or a directory such as a
 * fontstack of glyph PBFs) with its SPDX licence, source, credit, and, for a
 * font, its Reserved Font Name. Paths are relative to the repository root. The
 * check fails on a file in an asset directory without an entry, on a licence
 * that ADR 0016 does not allow, and on an incomplete or stale entry. The manifest
 * also feeds the credits on the About TART page. A unit test runs it in CI.
 */
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export interface Asset {
	path: string;
	licence: string;
	source: string;
	credit: string;
	reservedFontName?: string | null;
}

export interface AssetManifest {
	directories: string[];
	assets: Asset[];
}

const FONT_LICENCES = new Set(['OFL-1.1']);
const ALLOWED = new Set([
	...FONT_LICENCES,
	'CC0-1.0',
	'CC-BY-4.0',
	'MIT',
	'BSD-2-Clause',
	'BSD-3-Clause',
	'Apache-2.0',
	'ISC'
]);

const manifestFile = new URL('../third-party-assets.json', import.meta.url);
export const repositoryRoot = fileURLToPath(new URL('../..', import.meta.url));

export function loadAssetManifest(): AssetManifest {
	return JSON.parse(readFileSync(manifestFile, 'utf8'));
}

function filesUnder(root: string, directory: string): string[] {
	return readdirSync(path.join(root, directory), { recursive: true, withFileTypes: true })
		.filter((entry) => entry.isFile())
		.map((entry) => path.relative(root, path.join(entry.parentPath, entry.name)))
		.map((file) => file.split(path.sep).join('/'))
		.sort();
}

const covers = (asset: Asset, file: string) =>
	file === asset.path || file.startsWith(`${asset.path}/`);

export function assetManifestErrors(manifest: AssetManifest, root: string): string[] {
	const errors: string[] = [];
	for (const asset of manifest.assets) {
		const label = asset.path;
		if (!existsSync(path.join(root, asset.path)))
			errors.push(`${label}: no such file or directory`);
		if (!ALLOWED.has(asset.licence))
			errors.push(`${label}: ${asset.licence} is not allowed for an asset`);
		if (!asset.source) errors.push(`${label}: no source`);
		if (!asset.credit) errors.push(`${label}: no credit`);
		if (FONT_LICENCES.has(asset.licence) && asset.reservedFontName === undefined) {
			errors.push(`${label}: a font needs reservedFontName (null when it has none)`);
		}
		const reserved = asset.reservedFontName;
		if (reserved && asset.path.toLowerCase().includes(reserved.toLowerCase())) {
			errors.push(`${label}: the path uses the Reserved Font Name "${reserved}"`);
		}
	}
	for (const directory of manifest.directories) {
		if (!existsSync(path.join(root, directory))) {
			errors.push(`${directory}: no such asset directory`);
			continue;
		}
		for (const file of filesUnder(root, directory)) {
			if (!manifest.assets.some((asset) => covers(asset, file))) {
				errors.push(`${file}: no entry in the third-party asset manifest`);
			}
		}
	}
	return errors;
}

if (import.meta.main) {
	const errors = assetManifestErrors(loadAssetManifest(), repositoryRoot);
	console.log(errors.join('\n') || 'Every third-party asset has a valid manifest entry.');
	process.exitCode = errors.length > 0 ? 1 : 0;
}
