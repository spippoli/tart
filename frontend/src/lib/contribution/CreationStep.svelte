<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import CitationChoice from './CitationChoice.svelte';
	import { isEmptyDate } from './date-field';
	import { errorText } from './errors';
	import type { EditorState } from './state.svelte';
	import UncertainDateInput from './UncertainDateInput.svelte';
	import { ids } from './validate';

	/**
	 * The Creation date step, optional (Contribution and moderation spec, Form
	 * structure): when the Artwork was made, as an Uncertain date, which becomes its
	 * Creation event. The Claim may cite what supports it, and its Evidence level shows.
	 */
	let { editor }: { editor: EditorState } = $props();
	const config = $derived(editor.config);
	const form = $derived(editor.form);

	const citables = $derived(
		editor.citables(
			(item, index) =>
				item.medium === 'link'
					? m.editor_cite_link({ number: index + 1, url: item.url })
					: m.editor_cite_file({ number: index + 1, name: item.fileName }),
			(title) => m.editor_cite_source({ title: title || m.editor_untitled_source() })
		)
	);

	function message(id: string) {
		const found = editor.errorAt(id);
		return found ? errorText(found.code, found.params) : null;
	}
</script>

<div class="step">
	<p>{m.editor_creation_intro()}</p>
	<UncertainDateInput
		id={ids.creationDate}
		legend={m.editor_creation_legend()}
		bind:value={form.created.date}
		locale={config.locale}
		timeZone={config.timeZone}
		today={editor.today}
		optional
		error={message(ids.creationDate) ??
			message(`${ids.creationDate}-second`) ??
			message(`${ids.creationDate}-qualifier`)}
	/>
	{#if !isEmptyDate(form.created.date)}
		<CitationChoice
			id="editor-created-citations"
			legend={m.editor_creation_citations()}
			{citables}
			bind:selected={form.created.citations}
			locale={config.locale}
		/>
	{/if}
</div>

<style>
	.step {
		display: grid;
		gap: 1.25rem;
	}

	.step > p {
		margin: 0;
		max-inline-size: var(--measure);
	}
</style>
