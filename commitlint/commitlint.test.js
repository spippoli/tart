// Operations and portability, acceptance criterion 37: a pull request with a
// commit whose message is not a valid Conventional Commit fails the
// `commitlint` check. Each test builds a throwaway Git repository and runs the
// CLI over the range base..head, as the CI job does.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const packageDir = import.meta.dirname;
const config = join(packageDir, 'commitlint.config.js');
const cli = join(packageDir, 'node_modules', '.bin', 'commitlint');

const allowedTypes = [
	'feat',
	'fix',
	'docs',
	'refactor',
	'test',
	'chore',
	'ci',
	'build',
	'perf',
	'revert',
	'style'
];

function git(cwd, ...args) {
	return execFileSync('git', args, {
		cwd,
		encoding: 'utf8',
		env: {
			...process.env,
			GIT_AUTHOR_NAME: 'Test',
			GIT_AUTHOR_EMAIL: 'test@example.invalid',
			GIT_COMMITTER_NAME: 'Test',
			GIT_COMMITTER_EMAIL: 'test@example.invalid',
			GIT_CONFIG_GLOBAL: '/dev/null',
			GIT_CONFIG_NOSYSTEM: '1'
		}
	}).trim();
}

// A repository whose `main` has one commit; returns its path and that base.
function repository(t) {
	const dir = mkdtempSync(join(tmpdir(), 'tart-commitlint-'));
	t.after(() => rmSync(dir, { recursive: true, force: true }));
	git(dir, 'init', '--quiet', '--initial-branch=main');
	git(dir, 'commit', '--quiet', '--allow-empty', '-m', 'chore: initial commit');
	return { dir, base: git(dir, 'rev-parse', 'HEAD') };
}

function commit(dir, message) {
	git(dir, 'commit', '--quiet', '--allow-empty', '-m', message);
}

// Runs the check over base..HEAD and returns its exit status and output.
function lintRange(dir, base) {
	const result = spawnSync(cli, ['--config', config, '--cwd', dir, '--from', base, '--to', 'HEAD'], {
		cwd: dir,
		encoding: 'utf8'
	});
	return { status: result.status, output: result.stdout + result.stderr };
}

test('a pull request whose commits use each allowed type passes', (t) => {
	const { dir, base } = repository(t);
	for (const type of allowedTypes) commit(dir, `${type}: describe a ${type} change`);
	commit(dir, 'feat(backend): a scoped commit');
	commit(dir, 'fix!: a breaking commit\n\nBREAKING CHANGE: run tart upgrade 0.2.0.');
	const { status, output } = lintRange(dir, base);
	assert.equal(status, 0, output);
});

for (const [name, message] of [
	['a type ADR 0021 does not allow', 'feature: add the map view'],
	['no type', 'add the map view'],
	['an upper-case type', 'Feat: add the map view'],
	['an empty subject', 'feat: '],
	['a missing space after the colon', 'feat:add the map view'],
	['a header longer than 100 characters', `feat: ${'a'.repeat(100)}`]
]) {
	test(`a pull request with a commit with ${name} fails`, (t) => {
		const { dir, base } = repository(t);
		commit(dir, 'feat: a valid commit');
		commit(dir, message);
		const { status, output } = lintRange(dir, base);
		assert.equal(status, 1, output);
		// The failure names the offending message, not a configuration error.
		assert.ok(output.includes(message.trim()), output);
		assert.match(output, /found [1-9]\d* problems/);
	});
}

test('GitHub merge commits pass', (t) => {
	const { dir, base } = repository(t);
	git(dir, 'switch', '--quiet', '-c', 'feat/map');
	commit(dir, 'feat: add the map view');
	git(dir, 'switch', '--quiet', 'main');
	commit(dir, 'fix: a change on main');
	// "Update branch" merges the base into the pull request branch.
	git(dir, 'switch', '--quiet', 'feat/map');
	git(dir, 'merge', '--quiet', '--no-ff', '-m', "Merge branch 'main' into feat/map", 'main');
	git(dir, 'switch', '--quiet', 'main');
	git(dir, 'merge', '--quiet', '--no-ff', '-m', 'Merge pull request #12 from spippoli/feat/map', 'feat/map');
	const { status, output } = lintRange(dir, base);
	assert.equal(status, 0, output);
});
