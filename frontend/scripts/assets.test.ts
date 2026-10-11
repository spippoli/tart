import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import {
	type Asset,
	type AssetManifest,
	assetManifestErrors,
	loadAssetManifest,
	repositoryRoot
} from './assets.ts';

function repository(files: string[]): string {
	const root = mkdtempSync(path.join(tmpdir(), 'tart-assets-'));
	for (const file of files) {
		mkdirSync(path.dirname(path.join(root, file)), { recursive: true });
		writeFileSync(path.join(root, file), '');
	}
	return root;
}

const font: Asset = {
	path: 'map/fonts/Noto Sans Regular',
	licence: 'OFL-1.1',
	source: 'https://github.com/notofonts/latin-greek-cyrillic',
	credit: 'Noto Sans by Google',
	reservedFontName: null
};

describe('the third-party asset manifest check', () => {
	it('passes on the shipped manifest', () => {
		expect(assetManifestErrors(loadAssetManifest(), repositoryRoot)).toEqual([]);
	});

	it('passes when an entry covers every file of an asset directory', () => {
		const root = repository(['map/fonts/Noto Sans Regular/0-255.pbf', 'map/sprite.png']);
		const manifest: AssetManifest = {
			directories: ['map'],
			assets: [
				font,
				{
					path: 'map/sprite.png',
					licence: 'CC0-1.0',
					source: 'https://example.org',
					credit: 'Example'
				}
			]
		};

		expect(assetManifestErrors(manifest, root)).toEqual([]);
	});

	it('fails on a file in an asset directory without an entry', () => {
		const root = repository(['map/fonts/Noto Sans Regular/0-255.pbf', 'map/icons/pin.svg']);

		expect(assetManifestErrors({ directories: ['map'], assets: [font] }, root)).toEqual([
			'map/icons/pin.svg: no entry in the third-party asset manifest'
		]);
	});

	it.each(['CC-BY-SA-4.0', 'CC-BY-NC-4.0', 'CC-BY-ND-4.0', 'GPL-3.0-only'])(
		'fails on an asset under %s',
		(licence) => {
			const root = repository(['map/fonts/Noto Sans Regular/0-255.pbf']);

			expect(
				assetManifestErrors({ directories: ['map'], assets: [{ ...font, licence }] }, root)
			).toEqual([`map/fonts/Noto Sans Regular: ${licence} is not allowed for an asset`]);
		}
	);

	it('fails on an entry without its source, credit, or Reserved Font Name', () => {
		const root = repository(['map/fonts/Noto Sans Regular/0-255.pbf']);
		const incomplete = { path: font.path, licence: 'OFL-1.1', source: '', credit: '' };

		expect(assetManifestErrors({ directories: ['map'], assets: [incomplete] }, root)).toEqual([
			'map/fonts/Noto Sans Regular: no source',
			'map/fonts/Noto Sans Regular: no credit',
			'map/fonts/Noto Sans Regular: a font needs reservedFontName (null when it has none)'
		]);
	});

	it('fails on a fontstack named after its Reserved Font Name', () => {
		const root = repository(['map/fonts/Goudy Regular/0-255.pbf']);
		const reserved = { ...font, path: 'map/fonts/Goudy Regular', reservedFontName: 'Goudy' };

		expect(assetManifestErrors({ directories: ['map'], assets: [reserved] }, root)).toEqual([
			'map/fonts/Goudy Regular: the path uses the Reserved Font Name "Goudy"'
		]);
	});

	it('fails on an entry or an asset directory that does not exist', () => {
		const root = repository([]);

		expect(assetManifestErrors({ directories: ['map'], assets: [font] }, root)).toEqual([
			'map/fonts/Noto Sans Regular: no such file or directory',
			'map: no such asset directory'
		]);
	});
});
