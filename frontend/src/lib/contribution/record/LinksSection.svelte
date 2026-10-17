<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import ArtworkPicker from '../ArtworkPicker.svelte';
	import { errorText } from '../errors';
	import RecordPicker from '../RecordPicker.svelte';
	import type { LinkRef } from './form';
	import NewPlace from './NewPlace.svelte';
	import type { CollectionSpec } from './spec';
	import type { RecordEditorState } from './state.svelte';
	import { ids } from './validate';
	import { collectionLabel } from './words';

	/**
	 * A collection of links to other records (the Series of an Artwork, the Areas of an
	 * Artist's activity, the Artworks a Documentation item is about): what the record links to
	 * now, each of which can be removed, and the links this Submission adds. A Series can be
	 * created from here, with this Artwork as its first member (Other editors); the other
	 * kinds are picked among records that exist.
	 */
	let { editor, collection }: { editor: RecordEditorState; collection: CollectionSpec } = $props();
	const label = $derived(collectionLabel(collection.name));
	const delta = $derived(editor.form.links[collection.name]);
	const present = $derived(
		(Array.isArray(editor.config.current[collection.name])
			? (editor.config.current[collection.name] as unknown[])
			: []
		).filter((each): each is number => typeof each === 'number')
	);
	const found = $derived(editor.errorAt(ids.add(collection.name)));

	function remove(id: number, on: boolean) {
		delta.removed = on ? [...delta.removed, id] : delta.removed.filter((each) => each !== id);
	}

	function add(link: LinkRef) {
		const exists = delta.added.some((each) => each.id !== null && each.id === link.id);
		if (!exists && !present.includes(link.id ?? -1)) delta.added.push(link);
	}

	function drop(link: LinkRef) {
		delta.added = delta.added.filter((each) => each !== link);
		if (link.key !== null) {
			editor.form.series = editor.form.series.filter((each) => each.key !== link.key);
		}
	}

	function createSeries(name: string) {
		const key = editor.newKey('series');
		editor.form.series.push({ key, name, description: '', sources: [] });
		delta.added.push({ id: null, key, name });
	}
</script>

<section class="links" id={ids.collection(collection.name)} tabindex="-1">
	<h3>{label}</h3>

	{#if present.length > 0}
		<ul>
			{#each present as id (id)}
				{@const removed = delta.removed.includes(id)}
				<li>
					<span class:removed>{editor.name(id)}</span>
					{#if removed}
						<span class="state">{m.editor_item_removed()}</span>
						<button type="button" onclick={() => remove(id, false)}>
							{m.editor_item_keep({ name: editor.name(id) })}
						</button>
					{:else}
						<button type="button" onclick={() => remove(id, true)}>
							{m.editor_item_remove({ name: editor.name(id) })}
						</button>
					{/if}
				</li>
			{/each}
		</ul>
	{:else}
		<p>{m.editor_value_none()}</p>
	{/if}

	{#if delta.added.length > 0}
		<div class="proposal">
			<p><strong>{m.editor_proposed_label()}</strong></p>
			<ul>
				{#each delta.added as link (link.id ?? link.key)}
					<li>
						<span>{link.name}</span>
						{#if link.key !== null}<span class="state">{m.editor_item_new()}</span>{/if}
						<button type="button" onclick={() => drop(link)}>
							{m.editor_item_undo_add({ name: link.name })}
						</button>
					</li>
				{/each}
			</ul>
		</div>
		{#each editor.form.series.filter( (each) => delta.added.some((link) => link.key === each.key) ) as place (place.key)}
			<NewPlace
				{editor}
				{place}
				kind="series"
				onremove={() => {
					const link = delta.added.find((each) => each.key === place.key);
					if (link) drop(link);
				}}
			/>
		{/each}
	{/if}

	{#if collection.picker === 'series'}
		<RecordPicker
			{editor}
			kind="series"
			id={ids.add(collection.name)}
			label={m.editor_series_add()}
			onpick={(series) => add({ id: series.id, key: null, name: series.name })}
			oncreate={createSeries}
		/>
	{:else if collection.picker === 'areas'}
		<RecordPicker
			{editor}
			kind="area"
			id={ids.add(collection.name)}
			label={m.editor_areas_add()}
			onpick={(area) => add({ id: area.id, key: null, name: area.name })}
		/>
	{:else if collection.picker === 'artworks'}
		<ArtworkPicker
			id={ids.add(collection.name)}
			label={m.editor_artworks_add()}
			onpick={(artwork) => add({ id: artwork.id, key: null, name: artwork.title })}
		/>
	{/if}
	{#if found}
		<p class="error">
			<strong>{m.editor_error_prefix()}</strong>
			{errorText(found.code, found.params)}
		</p>
	{/if}
</section>

<style>
	.links {
		display: grid;
		gap: 0.75rem;
		justify-items: start;
		border-block-start: 1px solid var(--border);
		padding-block: 1rem 0.5rem;
	}

	h3,
	p {
		margin: 0;
	}

	ul {
		margin: 0;
		padding-inline-start: 1.25rem;
		display: grid;
		gap: 0.5rem;
	}

	.removed {
		text-decoration: line-through;
	}

	.state {
		font-variant-caps: all-small-caps;
		letter-spacing: 0.04em;
		margin-inline: 0.5rem;
	}

	.proposal {
		display: grid;
		gap: 0.5rem;
		inline-size: 100%;
		border: 3px dashed var(--text);
		padding: 0.75rem;
	}

	.error {
		border-inline-start: 4px solid var(--accent, currentColor);
		padding-inline-start: 0.5rem;
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
