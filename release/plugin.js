// The TART steps of semantic-release (ADR 0021), wrapped around the standard
// commit analyzer and release-notes generator.
import { appendFileSync } from 'node:fs';
import { analyzeCommits as analyze } from '@semantic-release/commit-analyzer';
import { generateNotes as generate } from '@semantic-release/release-notes-generator';
import { pullRequestsByCommit } from './pull-requests.js';

const major = (version) => Number(version.split('.')[0]);

/** The bump of the commit analyzer, except that while the major is 0 a
 * breaking commit gives a minor: versions stay at 0.x until launch. */
export async function analyzeCommits(pluginConfig, context) {
	const type = await analyze(pluginConfig, context);
	const { version } = context.lastRelease;
	if (type === 'major' && version && major(version) === 0) {
		context.logger.log('The major is 0, so the breaking change gives a minor release');
		return 'minor';
	}
	return type;
}

/**
 * Refuses a release without a previous tag, which semantic-release would number
 * 1.0.0: the one-time `v0.0.0` tag must exist first. When the images were built
 * for a version (`TART_RELEASE_VERSION`), refuses to tag any other. In GitHub
 * Actions, exposes the version as the step output `version`.
 */
export function verifyRelease(_pluginConfig, context) {
	const { lastRelease, nextRelease, env } = context;
	if (!lastRelease.version) {
		throw new Error('No release tag found: push the one-time v0.0.0 tag first (ADR 0021)');
	}
	const expected = env.TART_RELEASE_VERSION;
	if (expected && expected !== nextRelease.version) {
		throw new Error(
			`The images were built for ${expected}, but the next version is now ${nextRelease.version}`
		);
	}
	if (env.GITHUB_OUTPUT) appendFileSync(env.GITHUB_OUTPUT, `version=${nextRelease.version}\n`);
}

/** The release notes, each commit carrying the pull request that merged it. */
export async function generateNotes(pluginConfig, context) {
	const { cwd, commits, lastRelease, nextRelease } = context;
	const range = lastRelease.gitHead
		? `${lastRelease.gitHead}..${nextRelease.gitHead}`
		: nextRelease.gitHead;
	const pullRequests = pullRequestsByCommit(cwd, range);
	const withPullRequests = commits.map((commit) => ({
		...commit,
		pullRequest: pullRequests.get(commit.hash)
	}));
	return generate(pluginConfig, { ...context, commits: withPullRequests });
}
