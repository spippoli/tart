<script lang="ts">
	import { evidenceWords } from '#lib/archive/records.ts';
	import { m } from '#lib/paraglide/messages.js';
	import DocumentationStep from './DocumentationStep.svelte';
	import SourcesStep from './SourcesStep.svelte';
	import type { EditorState } from './state.svelte';

	/**
	 * The evidence of a History event (Contribution and moderation spec, Form structure):
	 * files and Sources, with the Evidence level it will have as a live readout in words,
	 * *reported* when nothing is cited (ADR 0006). Both are optional.
	 */
	let { editor }: { editor: EditorState } = $props();
	const cited = $derived(editor.form.documentation.length + editor.form.sources.length);
</script>

<div class="step">
	<p class="level" role="status">
		{m.editor_evidence_readout({
			level: evidenceWords(cited > 0 ? 'documented' : 'reported', cited, editor.config.locale)
		})}
	</p>
	<DocumentationStep {editor} />
	<SourcesStep {editor} />
</div>

<style>
	.step {
		display: grid;
		gap: 2rem;
	}

	.level {
		margin: 0;
		font-weight: 600;
	}
</style>
