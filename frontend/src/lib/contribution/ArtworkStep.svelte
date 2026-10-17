<script lang="ts">
	import { vocabularyLabels } from '#lib/archive/records.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { errorText } from './errors';
	import Field from './Field.svelte';
	import Group from './Group.svelte';
	import RecordPicker from './RecordPicker.svelte';
	import type { EditorState } from './state.svelte';
	import { ids } from './validate';

	/**
	 * The Artwork step (Contribution and moderation spec, Form structure): a title or an
	 * explicit *Untitled*, the Expression types (retired ones are not offered), a
	 * description, and the Series. Free text is archive content in the Content language.
	 */
	let { editor }: { editor: EditorState } = $props();
	const config = $derived(editor.config);
	const form = $derived(editor.form);
	const typeLabel = $derived(vocabularyLabels(config.expressionTypes, config.locale));
	const types = $derived(config.expressionTypes.filter((each) => each.retired === false));

	function message(id: string) {
		const found = editor.errorAt(id);
		return found ? errorText(found.code, found.params) : null;
	}

	function toggle(key: string, on: boolean) {
		form.expressionTypes = on
			? [...form.expressionTypes, key]
			: form.expressionTypes.filter((each) => each !== key);
	}

	function removeSeries(index: number) {
		form.series.splice(index, 1);
	}
</script>

<div class="step">
	<Field id={ids.title} label={m.editor_artwork_title()} error={message(ids.title)}>
		{#snippet children(props)}
			<input
				{...props}
				type="text"
				lang={config.contentLanguage}
				autocomplete="off"
				disabled={form.untitled}
				bind:value={form.title}
			/>
		{/snippet}
	</Field>
	<label class="check">
		<input
			type="checkbox"
			bind:checked={form.untitled}
			onchange={() => {
				if (form.untitled) form.title = '';
			}}
		/>
		{m.editor_artwork_untitled()}
	</label>

	<Group
		id={ids.expressionTypes}
		legend={m.editor_artwork_types()}
		hint={m.editor_artwork_types_hint()}
		error={message(ids.expressionTypes)}
	>
		{#snippet children({ invalid })}
			{#each types as type, index (type.key)}
				<label>
					<input
						id={index === 0 ? ids.expressionTypes : undefined}
						type="checkbox"
						checked={form.expressionTypes.includes(type.key)}
						aria-invalid={index === 0 ? invalid : undefined}
						onchange={(event) => toggle(type.key, event.currentTarget.checked)}
					/>
					{typeLabel(type.key)}
				</label>
			{/each}
		{/snippet}
	</Group>

	<Field id="editor-description" label={m.editor_artwork_description()}>
		{#snippet children(props)}
			<textarea {...props} rows="5" lang={config.contentLanguage} bind:value={form.description}
			></textarea>
		{/snippet}
	</Field>

	<section class="series" aria-labelledby="editor-series-title">
		<h3 id="editor-series-title">{m.editor_series_title()}</h3>
		<p class="hint">{m.editor_series_hint()}</p>
		{#if form.series.length > 0}
			<ul>
				{#each form.series as series, index (series.id ?? series.key)}
					<li>
						<span lang={config.contentLanguage}>{series.name}</span>
						{#if series.id === null}<span class="new">({m.editor_new()})</span>{/if}
						<button type="button" onclick={() => removeSeries(index)}>
							{m.editor_series_remove({ name: series.name })}
						</button>
					</li>
				{/each}
			</ul>
		{/if}
		<RecordPicker
			{editor}
			kind="series"
			id="editor-series-picker"
			label={m.editor_series_picker()}
			onpick={(record) => {
				if (!form.series.some((each) => each.id === record.id)) {
					form.series.push({ id: record.id, key: null, name: record.name });
				}
			}}
			oncreate={(name) => form.series.push({ id: null, key: editor.newKey('series'), name })}
		/>
	</section>
</div>

<style>
	.step {
		display: grid;
		gap: 1.25rem;
	}

	.check {
		display: flex;
		gap: 0.5rem;
		align-items: baseline;
		margin-block-start: -0.75rem;
	}

	.series {
		display: grid;
		gap: 0.75rem;
	}

	.series > * {
		margin: 0;
	}

	.hint {
		color: var(--text-muted);
	}

	ul {
		margin: 0;
		padding-inline-start: 1.25rem;
		display: grid;
		gap: 0.5rem;
	}

	button {
		min-block-size: 2.75rem;
		padding-inline: 0.75rem;
		background: var(--background);
		color: var(--text);
		border: 1px solid var(--border);
		cursor: pointer;
	}
</style>
