/**
 * Dependency licence allow-list for the JavaScript dependencies (ADR 0011 §8, ADR 0016 §3).
 *
 *     node scripts/licences.ts    (pnpm check:licences)
 *
 * Permissive licences are allowed for any package. Everything else needs a
 * reviewed entry in `licences.json` that records the exact licence:
 * - `weak-copyleft`: an unmodified library, which a person has to judge;
 * - `asset`: a font, icon, or design package under OFL-1.1, CC0-1.0, or CC-BY-4.0,
 *   so that a code package with an asset licence cannot slip through;
 * - `permissive`: a permissive licence that ADR 0011 does not name.
 * Strong copyleft can never be reviewed in. A unit test runs this check in CI.
 */
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';

export interface Dependency {
	name: string;
	version: string;
	licence: string;
}

export interface Reviewed {
	licence: string;
	tier: string;
	reason: string;
}

const PERMISSIVE = new Set([
	'MIT',
	'BSD-2-Clause',
	'BSD-3-Clause',
	'Apache-2.0',
	'ISC',
	'PSF-2.0',
	'Python-2.0',
	'Zlib'
]);
const WEAK_COPYLEFT = new Set([
	'LGPL-2.1-only',
	'LGPL-2.1-or-later',
	'LGPL-3.0-only',
	'LGPL-3.0-or-later',
	'MPL-2.0'
]);
const ASSET = new Set(['OFL-1.1', 'CC0-1.0', 'CC-BY-4.0']);
const isCopyleft = (licence: string) => /^(A?GPL|LGPL|MPL|CC-BY-SA|CC-BY-NC)/.test(licence);

const TIERS: Record<string, (licence: string) => boolean> = {
	'weak-copyleft': (licence) => PERMISSIVE.has(licence) || WEAK_COPYLEFT.has(licence),
	asset: (licence) => PERMISSIVE.has(licence) || ASSET.has(licence),
	permissive: (licence) => !isCopyleft(licence) && !ASSET.has(licence)
};

/** Evaluates an SPDX expression: OR takes any alternative, AND needs every part.
 * `X WITH exception` counts as `X`, since an SPDX exception only adds permissions. */
export function satisfies(expression: string, allowed: (licence: string) => boolean): boolean {
	const tokens = expression.match(/\(|\)|[A-Za-z0-9.+-]+/g) ?? [];
	let position = 0;
	const peek = () => tokens[position];
	const take = () => tokens[position++];

	function anyOf(): boolean {
		let result = allOf();
		while (peek() === 'OR') {
			take();
			result = allOf() || result;
		}
		return result;
	}
	function allOf(): boolean {
		let result = term();
		while (peek() === 'AND') {
			take();
			result = term() && result;
		}
		return result;
	}
	function term(): boolean {
		if (peek() === '(') {
			take();
			const result = anyOf();
			take(); // ")"
			return result;
		}
		const licence = take();
		if (peek() === 'WITH') position += 2;
		return allowed(licence);
	}

	const result = anyOf();
	if (position !== tokens.length) throw new Error(`invalid SPDX expression: ${expression}`);
	return result;
}

/** A reviewed name may end in `*` to cover a package's platform-specific binaries. */
function findReview(name: string, reviewed: Record<string, Reviewed>): Reviewed | undefined {
	return Object.entries(reviewed).find(([pattern]) =>
		pattern.endsWith('*') ? name.startsWith(pattern.slice(0, -1)) : name === pattern
	)?.[1];
}

export function violations(
	dependencies: Dependency[],
	reviewed: Record<string, Reviewed>
): string[] {
	const found: string[] = [];
	for (const { name, version, licence } of dependencies) {
		if (satisfies(licence, (id) => PERMISSIVE.has(id))) continue;
		const review = findReview(name, reviewed);
		const label = `${name} ${version}`;
		if (!review || review.licence !== licence) {
			found.push(`${label}: ${licence} is outside the licence tiers`);
		} else if (!Object.hasOwn(TIERS, review.tier) || !satisfies(licence, TIERS[review.tier])) {
			found.push(`${label}: the review of ${licence} as ${review.tier} does not fit that tier`);
		}
	}
	return found;
}

/** Every installed package, development tools included, as `pnpm licenses` reports it. */
export function installedDependencies(): Dependency[] {
	const output = execFileSync('pnpm', ['licenses', 'list', '--json'], {
		cwd: new URL('..', import.meta.url),
		encoding: 'utf8',
		maxBuffer: 64 * 1024 * 1024
	});
	const byLicence = JSON.parse(output) as Record<string, { name: string; versions: string[] }[]>;
	return Object.entries(byLicence).flatMap(([licence, packages]) =>
		packages.flatMap(({ name, versions }) =>
			versions.map((version) => ({ name, version, licence }))
		)
	);
}

export function loadReviewed(): Record<string, Reviewed> {
	const policy = JSON.parse(readFileSync(new URL('../licences.json', import.meta.url), 'utf8'));
	return policy.reviewed;
}

if (import.meta.main) {
	const found = violations(installedDependencies(), loadReviewed());
	console.log(found.join('\n') || 'Every dependency is within the licence tiers.');
	process.exitCode = found.length > 0 ? 1 : 0;
}
