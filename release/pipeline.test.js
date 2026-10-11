// Operations and portability, acceptance criteria 1, 3, 34, 35 and 36 (ADR 0021):
// what the release workflow, the Operator files, and the project files must hold.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { cpSync, existsSync, mkdtempSync, readFileSync, readdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, join } from 'node:path';
import { parse } from 'yaml';
import { assets } from './release.config.js';
import { installedDependencies, loadReviewed, violations } from '../frontend/scripts/licences.ts';

const root = new URL('../', import.meta.url);
const read = (path) => readFileSync(new URL(path, root), 'utf8');
const workflow = parse(read('.github/workflows/release.yml'));
const production = parse(read('deploy/compose.yaml'));
const development = parse(read('deploy/compose.dev.yaml'));

const IMAGES = {
	api: 'ghcr.io/spippoli/tart-api',
	frontend: 'ghcr.io/spippoli/tart-frontend'
};
const PINNED = /^(ghcr\.io\/spippoli\/tart-(?:api|frontend)):\$\{TART_VERSION:\?[^}]*\}$/;

/** Every job the given job waits for, directly or not. */
function prerequisites(name) {
	const needs = [workflow.jobs[name].needs ?? []].flat();
	return new Set(needs.flatMap((need) => [need, ...prerequisites(need)]));
}

// Criterion 1.

test('the production Compose file runs the released images at TART_VERSION, never built', () => {
	assert.equal(production.services.api.image.match(PINNED)?.[1], IMAGES.api);
	assert.equal(production.services.worker.image, production.services.api.image);
	assert.equal(production.services.frontend.image.match(PINNED)?.[1], IMAGES.frontend);
	for (const [name, service] of Object.entries(production.services)) {
		assert.equal(service.build, undefined, `${name} has a build`);
		assert.doesNotMatch(service.image, /:latest$|^[^:@]+$/, `${name} floats`);
	}
});

test('the development Compose file builds the TART images from source', () => {
	assert.equal(development.services.api.build, '../backend');
	assert.equal(development.services.worker.build, '../backend');
	assert.equal(development.services.frontend.build, '../frontend');
	assert.deepEqual(development.services.mailpit.profiles, ['dev']);
});

test('each image is built natively for amd64 and arm64', () => {
	const { matrix } = workflow.jobs.build.strategy;
	assert.deepEqual(matrix.image, ['api', 'frontend']);
	assert.deepEqual(matrix.arch, ['amd64', 'arm64']);
	const runners = Object.fromEntries(
		matrix.include.filter((entry) => entry.runner).map(({ arch, runner }) => [arch, runner])
	);
	assert.deepEqual(runners, { amd64: 'ubuntu-24.04', arm64: 'ubuntu-24.04-arm' });

	const build = workflow.jobs.build.steps.find((step) => step.id === 'build');
	assert.equal(build.with.platforms, 'linux/${{ matrix.arch }}');
	assert.match(build.with.outputs, /name=ghcr\.io\/spippoli\/tart-\$\{\{ matrix\.image \}\},push-by-digest=true/);
});

test('the images carry the OCI labels version, revision, source, and licenses', () => {
	const build = workflow.jobs.build.steps.find((step) => step.id === 'build');
	const labels = Object.fromEntries(
		build.with.labels
			.trim()
			.split('\n')
			.map((line) => line.split(/=(.*)/s).slice(0, 2))
	);
	assert.deepEqual(labels, {
		'org.opencontainers.image.version': '${{ env.VERSION }}',
		'org.opencontainers.image.revision': '${{ github.sha }}',
		'org.opencontainers.image.source': '${{ github.server_url }}/${{ github.repository }}',
		'org.opencontainers.image.licenses': 'PolyForm-Noncommercial-1.0.0'
	});
});

test('the only tag pushed is the exact version', () => {
	const pushed = Object.values(workflow.jobs)
		.flatMap((job) => job.steps)
		.flatMap((step) => [...(step.run ?? '').matchAll(/--tag "([^"]+)"/g)].map((match) => match[1]));
	assert.deepEqual(pushed, ['$IMAGE:$VERSION']);
	assert.equal(workflow.jobs['tag-images'].env.IMAGE, 'ghcr.io/spippoli/tart-${{ matrix.image }}');
	assert.equal(workflow.jobs['tag-images'].env.VERSION, '${{ needs.version.outputs.version }}');
});

test('the arm64 api image is smoke-tested on an arm64 runner', () => {
	const { smoke } = workflow.jobs;
	assert.equal(smoke['runs-on'], 'ubuntu-24.04-arm');
	assert.ok(smoke.steps.some((step) => step.with?.name === 'digest-api-arm64'));
	assert.ok(smoke.steps.some((step) => step.run?.startsWith('release/smoke-test.sh')));
});

// Criterion 3.

test('the Instance never checks for updates', () => {
	const sources = (dir) =>
		readdirSync(new URL(dir, root), { recursive: true, withFileTypes: true })
			.filter((entry) => entry.isFile() && /\.(py|ts|js|svelte)$/.test(entry.name))
			.map((entry) => join(entry.parentPath, entry.name));
	for (const file of [...sources('backend/src/'), ...sources('frontend/src/')]) {
		assert.doesNotMatch(
			readFileSync(file, 'utf8'),
			/api\.github\.com|github\.com\/spippoli\/tart\/releases|ghcr\.io/,
			file
		);
	}
});

// Criterion 34.

test('the release is started by hand, on main only, one at a time', () => {
	assert.deepEqual(Object.keys(workflow.on), ['workflow_dispatch']);
	assert.equal(workflow.jobs.version.if, "github.ref == 'refs/heads/main'");
	assert.equal(workflow.concurrency['cancel-in-progress'], false);
	assert.ok(workflow.concurrency.group);
});

test('the tag and the GitHub Release come only after every image is pushed', () => {
	const runs = (name) => workflow.jobs[name].steps.map((step) => step.run ?? '').join('\n');
	const publishing = Object.keys(workflow.jobs).filter((name) =>
		/semantic-release(?! --dry-run)/.test(runs(name))
	);
	assert.deepEqual(publishing, ['release']);
	assert.deepEqual(
		prerequisites('release'),
		new Set(['version', 'build', 'smoke', 'tag-images'])
	);
	assert.match(runs('version'), /semantic-release --dry-run/);
});

// Criterion 35.

test('the repository project files stay at 0.0.0', () => {
	assert.match(read('backend/pyproject.toml'), /^version = "0\.0\.0"$/m);
	assert.equal(JSON.parse(read('frontend/package.json')).version, '0.0.0');
});

test('the release writes its version into both project files, without committing', (t) => {
	const dir = mkdtempSync(join(tmpdir(), 'tart-version-'));
	t.after(() => rmSync(dir, { recursive: true, force: true }));
	for (const file of ['backend/pyproject.toml', 'backend/uv.lock', 'frontend/package.json']) {
		cpSync(new URL(file, root), join(dir, file));
	}
	execFileSync(new URL('set-version.sh', import.meta.url).pathname, ['0.3.0', dir], {
		stdio: 'ignore'
	});

	const at = (file) => readFileSync(join(dir, file), 'utf8');
	assert.match(at('backend/pyproject.toml'), /^version = "0\.3\.0"$/m);
	assert.match(at('backend/uv.lock'), /name = "tart"\nversion = "0\.3\.0"/);
	assert.equal(JSON.parse(at('frontend/package.json')).version, '0.3.0');

	const build = workflow.jobs.build.steps;
	const written = build.findIndex((step) => step.run === 'release/set-version.sh "$VERSION"');
	assert.ok(written >= 0 && written < build.findIndex((step) => step.id === 'build'));
	const everyRun = Object.values(workflow.jobs)
		.flatMap((job) => job.steps)
		.map((step) => step.run ?? '');
	assert.ok(everyRun.every((run) => !/\bgit (commit|push)\b/.test(run)));
});

// Criterion 36.

test('each release attaches compose.yaml, Caddyfile, and .env.example', () => {
	const paths = assets.map(({ path }) => new URL(path, import.meta.url));
	assert.deepEqual(paths.map((path) => basename(path.pathname)), [
		'compose.yaml',
		'Caddyfile',
		'.env.example'
	]);
	assert.ok(paths.every((path) => existsSync(path)));
});

// The licence allow-list of ADR 0011 also covers these CI tools.

test('every release dependency is within the licence tiers', () => {
	const here = new URL('./', import.meta.url);
	assert.deepEqual(violations(installedDependencies(here), loadReviewed(here)), []);
});
