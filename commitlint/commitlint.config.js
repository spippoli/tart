// Commit messages are release inputs (ADR 0021): semantic-release reads them
// to compute the next version and write the release notes.
export default {
	extends: ['@commitlint/config-conventional'],
	rules: {
		// The types ADR 0021 allows, and no others.
		'type-enum': [
			2,
			'always',
			['feat', 'fix', 'docs', 'refactor', 'test', 'chore', 'ci', 'build', 'perf', 'revert', 'style']
		]
	}
};
