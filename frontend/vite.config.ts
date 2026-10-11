import { defineConfig } from 'vitest/config';
import adapter from '@sveltejs/adapter-node';
import { sveltekit } from '@sveltejs/kit/vite';
import { paraglideVitePlugin } from '@inlang/paraglide-js';
import { messageKeysCheck } from './scripts/messages.ts';
import packageJson from './package.json' with { type: 'json' };

const inlangProject = './project.inlang';

export default defineConfig({
	define: {
		// The TART version, which a release writes into package.json (ADR 0021).
		__TART_VERSION__: JSON.stringify(packageJson.version)
	},
	plugins: [
		messageKeysCheck(inlangProject),
		paraglideVitePlugin({ project: inlangProject, outdir: './src/lib/paraglide' }),
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			adapter: adapter()
		})
	],
	test: {
		expect: { requireAssertions: true },
		passWithNoTests: true,
		environment: 'node',
		include: ['src/**/*.{test,spec}.{js,ts}', 'scripts/**/*.test.ts']
	}
});
