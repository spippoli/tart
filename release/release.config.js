// semantic-release configuration of the release workflow (ADR 0021). It runs
// from this directory: `semantic-release --dry-run` computes the version, and
// after the images are pushed `semantic-release` tags and publishes the
// GitHub Release.
import { readFileSync } from 'node:fs';

const file = (path) => readFileSync(new URL(path, import.meta.url), 'utf8');

/** Options of the commit analyzer and the release-notes generator. */
export const conventions = {
	preset: 'conventionalcommits',
	// A custom rule replaces the default ones for the commits it matches, so the
	// breaking rule is repeated for a breaking `build(deps)`.
	releaseRules: [
		{ breaking: true, release: 'major' },
		{ type: 'build', scope: 'deps', release: 'patch' }
	],
	presetConfig: {
		// The sections of the notes, in order; commits of other types are left out.
		types: [
			{ type: 'feat', section: 'Features' },
			{ type: 'fix', section: 'Bug fixes' },
			{ type: 'perf', section: 'Performance' },
			{ type: 'revert', section: 'Reverts' },
			{ type: 'build', scope: 'deps', section: 'Dependency updates' }
		]
	},
	writerOpts: {
		// "Operator actions" opens the notes; the release title carries the version.
		mainTemplate: file('./notes/main.hbs'),
		headerPartial: '',
		commitPartial: file('./notes/commit.hbs'),
		footerPartial: ''
	}
};

/** The Operator files attached to each release, as separate assets. */
export const assets = [
	{ path: '../deploy/compose.yaml', label: 'compose.yaml' },
	{ path: '../deploy/Caddyfile', label: 'Caddyfile' },
	{ path: '../deploy/.env.example', label: '.env.example' }
];

export default {
	branches: ['main'],
	tagFormat: 'v${version}',
	plugins: [
		[new URL('./plugin.js', import.meta.url).pathname, conventions],
		[
			'@semantic-release/github',
			{
				assets,
				// The release feed is the announcement: no comments or labels on
				// issues and pull requests, and no issue when a release fails.
				successComment: false,
				failComment: false,
				releasedLabels: false
			}
		]
	]
};
