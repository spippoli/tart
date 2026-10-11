// Operations and portability, acceptance criteria 2 and 33 (ADR 0021): the
// semantic-release configuration, in dry-run mode over fixture commit
// histories in throwaway Git repositories, gives the expected next version for
// each bump rule and renders the release notes. The GitHub plugin is left out:
// it needs GitHub; everything else is the configuration the workflow runs.
// `pnpm test` runs the tests in-process (`--test-isolation=none`): semantic-release
// hooks stdout, which would corrupt the protocol of a test subprocess.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { Writable } from 'node:stream';
import semanticRelease from 'semantic-release';
import config from './release.config.js';

// The fixture repositories answer to the real repository's URL, so the notes
// carry the links they will have on GitHub.
const REPOSITORY_URL = 'https://github.com/spippoli/tart.git';
const COMMITS = 'https://github.com/spippoli/tart/commit/';
const PULLS = 'https://github.com/spippoli/tart/pull/';

// Every plugin of the release configuration except the GitHub one.
const plugins = config.plugins.filter(([name]) => name !== '@semantic-release/github');

function environment(origin) {
	return {
		PATH: process.env.PATH,
		HOME: process.env.HOME,
		GIT_AUTHOR_NAME: 'Test',
		GIT_AUTHOR_EMAIL: 'test@example.invalid',
		GIT_COMMITTER_NAME: 'Test',
		GIT_COMMITTER_EMAIL: 'test@example.invalid',
		GIT_CONFIG_GLOBAL: '/dev/null',
		GIT_CONFIG_NOSYSTEM: '1',
		GIT_CONFIG_COUNT: '1',
		GIT_CONFIG_KEY_0: `url.${origin}.insteadOf`,
		GIT_CONFIG_VALUE_0: REPOSITORY_URL
	};
}

/** A clone of an empty `main` whose remote is a bare repository. With a
 * `tag`, its first commit carries that tag, as `v0.0.0` does in TART. */
function repository(t, { tag = 'v0.0.0' } = {}) {
	const root = mkdtempSync(join(tmpdir(), 'tart-release-'));
	t.after(() => rmSync(root, { recursive: true, force: true }));
	const origin = join(root, 'origin.git');
	const env = environment(origin);
	const git = (...args) =>
		execFileSync('git', args, { cwd: dir, env, encoding: 'utf8' }).trim();
	const dir = join(root, 'work');

	execFileSync('git', ['init', '--quiet', '--bare', '--initial-branch=main', origin], { env });
	execFileSync('git', ['clone', '--quiet', REPOSITORY_URL, dir], { env, stdio: 'ignore' });
	git('switch', '--quiet', '--create', 'main');
	git('commit', '--quiet', '--allow-empty', '--message', 'chore: start the repository');
	if (tag) git('tag', tag);

	const repo = {
		dir,
		env,
		git,
		commit(message) {
			git('commit', '--quiet', '--allow-empty', '--message', message);
			return repo;
		},
		/** Merges a branch holding `messages` as GitHub merges pull request `number`. */
		pullRequest(number, ...messages) {
			git('switch', '--quiet', '--create', `pr-${number}`);
			messages.forEach((message) => repo.commit(message));
			git('switch', '--quiet', 'main');
			git(
				'merge',
				'--quiet',
				'--no-ff',
				'--message',
				`Merge pull request #${number} from fixture/pr-${number}`,
				`pr-${number}`
			);
			return repo;
		},
		tag(name) {
			git('tag', name);
			return repo;
		}
	};
	return repo;
}

const sink = () =>
	new Writable({
		write(_chunk, _encoding, done) {
			done();
		}
	});

/** semantic-release in dry-run mode, as the workflow's first job runs it. */
async function dryRun(repo, env = {}) {
	repo.git('push', '--quiet', '--follow-tags', 'origin', 'main');
	repo.git('push', '--quiet', '--tags', 'origin');
	const result = await semanticRelease(
		{
			branches: config.branches,
			tagFormat: config.tagFormat,
			plugins,
			repositoryUrl: REPOSITORY_URL,
			dryRun: true,
			ci: false
		},
		{ cwd: repo.dir, env: { ...repo.env, ...env }, stdout: sink(), stderr: sink() }
	);
	return result || undefined;
}

const nextVersion = async (repo) => (await dryRun(repo))?.nextRelease.version;
const notes = async (repo) => (await dryRun(repo)).nextRelease.notes;

// Criterion 33: the bump rules.

for (const [message, expected] of [
	['fix: keep the map centred', '0.0.1'],
	['perf: index the artworks by area', '0.0.1'],
	['build(deps): update the Python base image', '0.0.1'],
	['feat: record a history event', '0.1.0']
]) {
	test(`"${message}" after 0.0.0 gives ${expected}`, async (t) => {
		assert.equal(await nextVersion(repository(t).commit(message)), expected);
	});
}

for (const message of [
	'build: pin the frontend base image',
	'chore: tidy the ignore files',
	'ci: cache the dependencies',
	'docs: explain the backups',
	'refactor: split the loader',
	'style: format the backend',
	'test: cover the health endpoint'
]) {
	test(`"${message}" alone gives no release`, async (t) => {
		assert.equal(await nextVersion(repository(t).commit(message)), undefined);
	});
}

test('the highest bump of the commits wins', async (t) => {
	const repo = repository(t).commit('fix: keep the map centred').commit('feat: add Areas');
	assert.equal(await nextVersion(repo), '0.1.0');
});

test('while the major is 0, a breaking commit gives a minor', async (t) => {
	const bang = repository(t).tag('v0.3.1').commit('feat!: rename the configuration keys');
	assert.equal(await nextVersion(bang), '0.4.0');

	const footer = repository(t)
		.tag('v0.3.1')
		.commit('fix: drop the old setting\n\nBREAKING CHANGE: Remove `map.legacy` from instance.toml.');
	assert.equal(await nextVersion(footer), '0.4.0');
});

test('from 1.0.0, a breaking commit gives a major', async (t) => {
	const repo = repository(t).tag('v1.0.0').commit('feat!: rename the configuration keys');
	assert.equal(await nextVersion(repo), '2.0.0');
});

test('from 1.0.0, feat gives a minor and fix a patch', async (t) => {
	assert.equal(await nextVersion(repository(t).tag('v1.2.3').commit('feat: add Series')), '1.3.0');
	assert.equal(await nextVersion(repository(t).tag('v1.2.3').commit('fix: escape names')), '1.2.4');
});

test('a breaking build(deps) commit still gives a breaking bump', async (t) => {
	const repo = repository(t)
		.tag('v1.0.0')
		.commit('build(deps)!: move to PostgreSQL 19\n\nBREAKING CHANGE: Upgrade the database.');
	assert.equal(await nextVersion(repo), '2.0.0');
});

test('without the v0.0.0 tag, nothing is released', async (t) => {
	const repo = repository(t, { tag: null }).commit('feat: record a history event');
	await assert.rejects(dryRun(repo), /tag the first commit of the pipeline v0\.0\.0/);
});

test('the version is a step output for the workflow', async (t) => {
	const repo = repository(t).commit('feat: record a history event');
	const output = join(repo.dir, '..', 'github-output');
	writeFileSync(output, '');
	await dryRun(repo, { GITHUB_OUTPUT: output });
	assert.equal(readFileSync(output, 'utf8'), 'version=0.1.0\n');
});

test('a release refuses a version other than the one the images were built for', async (t) => {
	const repo = repository(t).commit('feat: record a history event');
	await assert.rejects(
		dryRun(repo, { TART_RELEASE_VERSION: '0.0.1' }),
		/built for 0\.0\.1, but the next version is now 0\.1\.0/
	);
	const result = await dryRun(repo, { TART_RELEASE_VERSION: '0.1.0' });
	assert.equal(result.nextRelease.version, '0.1.0');
});

// Criterion 2: the notes open with "Operator actions".

test('without a breaking commit, the notes say only the upgrade is needed', async (t) => {
	const repo = repository(t)
		.pullRequest(12, 'feat(map): show approximate Locations', 'test: cover the map')
		.pullRequest(13, 'fix: keep the map centred, closes #9');
	const fix = repo.git('rev-parse', 'HEAD^2');
	const text = await notes(repo);

	assert.ok(text.startsWith('## Operator actions\n\nOnly `tart upgrade 0.1.0` is needed.\n'), text);
	assert.match(text, /\n## Features\n\n\* \*\*map:\*\* show approximate Locations \(\[\w{7}\]/);
	assert.match(text, /\n## Bug fixes\n\n\* keep the map centred/);
	assert.ok(text.includes(`(${COMMITS}${fix})`), text);
	assert.ok(text.includes(`([#13](${PULLS}13))`), text);
	assert.ok(text.includes(`([#12](${PULLS}12))`), text);
	assert.ok(!text.includes('cover the map'), text);
	assert.ok(text.indexOf('## Features') < text.indexOf('## Bug fixes'), text);
});

test('a ticket merged through an integration pull request links the ticket', async (t) => {
	const repo = repository(t);
	repo.git('switch', '--quiet', '--create', 'dev/wave');
	repo.pullRequest(21, 'feat: add Series');
	repo.git('switch', '--quiet', 'main');
	repo.git('merge', '--quiet', '--no-ff', '--message', 'Merge pull request #30 from x/dev', 'dev/wave');
	const text = await notes(repo);
	assert.ok(text.includes(`([#21](${PULLS}21))`), text);
	assert.ok(!text.includes(`${PULLS}30`), text);
});

test('with breaking commits, the notes list each footer as an Operator action', async (t) => {
	const repo = repository(t)
		.tag('v1.4.0')
		.commit(
			'feat(config)!: split the map settings\n\nBREAKING CHANGE: Set `config_version = 2` and move `map.*` to `[map]`.'
		)
		.commit('fix!: stop serving old dumps\n\nBREAKING CHANGE: Delete `dumps/` from the data volume.')
		.commit('feat: add Areas');
	const text = await notes(repo);

	assert.ok(text.startsWith('## Operator actions\n\n'), text);
	assert.ok(
		text.includes('* **config:** Set `config_version = 2` and move `map.*` to `[map]`.\n'),
		text
	);
	assert.ok(text.includes('* Delete `dumps/` from the data volume.\n'), text);
	assert.ok(!text.includes('Only `tart upgrade'), text);
	assert.ok(text.indexOf('Delete `dumps/`') < text.indexOf('## Features'), text);
});

test('a CVE rebuild says that only the upgrade is needed', async (t) => {
	const repo = repository(t).tag('v0.3.0').commit('build(deps): update the Node base image');
	const text = await notes(repo);

	assert.ok(text.startsWith('## Operator actions\n\nOnly `tart upgrade 0.3.1` is needed.\n'), text);
	assert.match(text, /\n## Dependency updates\n\n\* \*\*deps:\*\* update the Node base image/);
});
