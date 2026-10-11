import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { tartVersion } from './version';

const packageJson = JSON.parse(
	readFileSync(new URL('../../package.json', import.meta.url), 'utf8')
) as { version: string };

describe('the TART version', () => {
	it('is the version in package.json, which a release sets', () => {
		expect(tartVersion).toBe(packageJson.version);
	});
});
