// Finds the pull request that brought each commit into the release, so that
// the release notes can link it (ADR 0021). Pull requests land on `main` as
// GitHub merge commits ("Merge pull request #N from ..."); a commit belongs to
// the innermost one that merged it, so a ticket merged into an integration
// branch is credited to the ticket's pull request, not to the integration one.
import { execFileSync } from 'node:child_process';

const MERGE_SUBJECT = /^Merge pull request #(\d+) from /;

function git(cwd, ...args) {
	return execFileSync('git', args, { cwd, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 }).trim();
}

const lines = (output) => (output ? output.split('\n') : []);

/**
 * Maps each commit hash in `range` (a `git log` revision range) to the number
 * of the pull request that merged it.
 */
export function pullRequestsByCommit(cwd, range) {
	const merges = lines(git(cwd, 'log', '--merges', '--format=%H %P%x09%s', range)).flatMap(
		(line) => {
			const [hashes, subject] = line.split('\t');
			const [, base, head] = hashes.split(' ');
			const number = MERGE_SUBJECT.exec(subject)?.[1];
			if (!number || !head) return [];
			return [{ number: Number(number), commits: lines(git(cwd, 'rev-list', `${base}..${head}`)) }];
		}
	);
	merges.sort((a, b) => a.commits.length - b.commits.length);

	const byCommit = new Map();
	for (const { number, commits } of merges) {
		for (const commit of commits) {
			if (!byCommit.has(commit)) byCommit.set(commit, number);
		}
	}
	return byCommit;
}
