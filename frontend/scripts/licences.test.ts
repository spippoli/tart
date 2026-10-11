import { describe, expect, it } from 'vitest';
import {
	type Dependency,
	type Reviewed,
	installedDependencies,
	loadReviewed,
	violations
} from './licences.ts';

const dep = (licence: string, name = 'pkg'): Dependency => ({ name, version: '1.0', licence });

describe('the dependency licence allow-list', () => {
	it('passes on the installed dependencies', () => {
		expect(violations(installedDependencies(), loadReviewed())).toEqual([]);
	});

	it.each([
		'MIT',
		'BSD-2-Clause',
		'Apache-2.0',
		'ISC',
		'Python-2.0',
		'Zlib',
		'(MIT OR CC0-1.0)',
		'(Apache-2.0 WITH LLVM-exception)',
		'MIT AND (BSD-3-Clause OR GPL-2.0-only)'
	])('allows the permissive licence %s for any dependency', (licence) => {
		expect(violations([dep(licence)], {})).toEqual([]);
	});

	it.each(['GPL-3.0-only', 'AGPL-3.0-only', 'MPL-2.0', 'OFL-1.1', 'CC-BY-4.0', 'Unknown'])(
		'refuses %s when the package is not reviewed',
		(licence) => {
			expect(violations([dep(licence)], {})).toEqual([
				`pkg 1.0: ${licence} is outside the licence tiers`
			]);
		}
	);

	it('allows a reviewed weak-copyleft package, platform variants included', () => {
		const reviewed: Record<string, Reviewed> = {
			'native-*': { licence: 'MPL-2.0', tier: 'weak-copyleft', reason: 'build tool' }
		};

		expect(violations([dep('MPL-2.0', 'native-linux-x64-gnu')], reviewed)).toEqual([]);
	});

	it('allows an asset licence only for a package listed by name (ADR 0016)', () => {
		const reviewed: Record<string, Reviewed> = {
			'@fontsource/noto-sans': { licence: 'OFL-1.1', tier: 'asset', reason: 'font' }
		};

		expect(violations([dep('OFL-1.1', '@fontsource/noto-sans')], reviewed)).toEqual([]);
		expect(violations([dep('OFL-1.1', 'some-code')], reviewed)).toHaveLength(1);
	});

	it('refuses a package whose licence changed since its review', () => {
		const reviewed: Record<string, Reviewed> = {
			pkg: { licence: 'MPL-2.0', tier: 'weak-copyleft', reason: 'build tool' }
		};

		expect(violations([dep('GPL-3.0-only')], reviewed)).toEqual([
			'pkg 1.0: GPL-3.0-only is outside the licence tiers'
		]);
	});

	it('never lets a review admit strong copyleft or a share-alike asset', () => {
		const reviewed: Record<string, Reviewed> = {
			pkg: { licence: 'GPL-3.0-only', tier: 'weak-copyleft', reason: '' },
			art: { licence: 'CC-BY-SA-4.0', tier: 'asset', reason: '' }
		};

		expect(violations([dep('GPL-3.0-only'), dep('CC-BY-SA-4.0', 'art')], reviewed)).toEqual([
			'pkg 1.0: the review of GPL-3.0-only as weak-copyleft does not fit that tier',
			'art 1.0: the review of CC-BY-SA-4.0 as asset does not fit that tier'
		]);
	});
});
