<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import { errorText } from '../errors';
	import Field from '../Field.svelte';
	import Group from '../Group.svelte';
	import type { NewSite } from './form';
	import type { RecordEditorState } from './state.svelte';
	import { ids } from './validate';

	/**
	 * A Site or a Series created from a field of the record (Contribution and moderation
	 * spec, Other editors): its name, an optional description, and the Sources of this
	 * Submission that support it. The record it is created from is its first member; it
	 * never exists without it. The name is checked against the archive's by the name rule
	 * when the picker offered it (it never blocks).
	 */
	let {
		editor,
		place,
		kind,
		onremove
	}: {
		editor: RecordEditorState;
		place: NewSite;
		kind: 'site' | 'series';
		onremove: () => void;
	} = $props();
	const config = $derived(editor.config);

	function message(id: string) {
		const found = editor.errorAt(id);
		return found ? errorText(found.code, found.params) : null;
	}

	function toggle(key: string, on: boolean) {
		place.sources = on ? [...place.sources, key] : place.sources.filter((each) => each !== key);
	}
</script>

<fieldset class="place">
	<legend>{kind === 'site' ? m.editor_new_site() : m.editor_new_series()}</legend>
	<p class="hint">{kind === 'site' ? m.editor_new_site_hint() : m.editor_new_series_hint()}</p>
	<Field
		id={ids.created(place.key, 'name')}
		label={m.editor_field_name()}
		error={message(ids.created(place.key, 'name'))}
	>
		{#snippet children(props)}
			<input
				{...props}
				type="text"
				lang={config.contentLanguage}
				autocomplete="off"
				bind:value={place.name}
			/>
		{/snippet}
	</Field>
	<Field id={ids.created(place.key, 'description')} label={m.editor_field_description()}>
		{#snippet children(props)}
			<textarea {...props} rows="2" lang={config.contentLanguage} bind:value={place.description}
			></textarea>
		{/snippet}
	</Field>
	{#if editor.form.sources.length > 0}
		<Group id={ids.created(place.key, 'sources')} legend={m.editor_new_place_sources()}>
			{#each editor.form.sources as source (source.key)}
				<label>
					<input
						type="checkbox"
						checked={place.sources.includes(source.key)}
						onchange={(event) => toggle(source.key, event.currentTarget.checked)}
					/>
					{m.editor_cite_source({ title: source.title || m.editor_untitled_source() })}
				</label>
			{/each}
		</Group>
	{/if}
	<button type="button" onclick={onremove}>{m.editor_new_place_remove()}</button>
</fieldset>

<style>
	.place {
		display: grid;
		gap: 1rem;
		justify-items: start;
		border: 1px solid var(--border);
		margin: 0;
		padding: 1rem;
	}

	.place legend {
		font-weight: 600;
	}

	.hint {
		margin: 0;
		color: var(--text-muted);
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
