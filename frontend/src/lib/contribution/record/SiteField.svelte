<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import RecordPicker from '../RecordPicker.svelte';
	import NewPlace from './NewPlace.svelte';
	import type { SiteValue } from './form';
	import type { RecordEditorState } from './state.svelte';

	/**
	 * The Site field of a Location (Contribution and moderation spec, Other editors):
	 * membership is held by the Location, so this is where a Location joins or leaves a
	 * Site, and where a new Site is created, with the Location as its first member. Other
	 * Locations join through their own edits.
	 */
	let {
		id,
		editor,
		value = $bindable()
	}: { id: string; editor: RecordEditorState; value: SiteValue } = $props();

	const created = $derived.by(() => {
		const site = value;
		return site.kind === 'new'
			? editor.form.sites.find((each) => each.key === site.key)
			: undefined;
	});

	function createNew(name: string) {
		const key = editor.newKey('site');
		editor.form.sites.push({ key, name, description: '', sources: [] });
		value = { kind: 'new', key };
	}

	function discardNew() {
		if (value.kind === 'new') {
			const key = value.key;
			editor.form.sites = editor.form.sites.filter((each) => each.key !== key);
		}
		value = { kind: 'none' };
	}
</script>

<div class="site" {id} tabindex="-1">
	{#if value.kind === 'existing'}
		<p>
			{m.editor_site_chosen({ name: value.name })}
			<button type="button" onclick={() => (value = { kind: 'none' })}>
				{m.editor_site_leave()}
			</button>
		</p>
	{:else if value.kind === 'new' && created}
		<NewPlace {editor} place={created} kind="site" onremove={discardNew} />
	{:else}
		<p>{m.editor_site_none()}</p>
		<RecordPicker
			{editor}
			kind="site"
			id="{id}-picker"
			label={m.editor_site_search()}
			onpick={(site) => (value = { kind: 'existing', id: site.id, name: site.name })}
			oncreate={createNew}
		/>
	{/if}
</div>

<style>
	.site {
		display: grid;
		gap: 0.75rem;
		justify-items: start;
	}

	p {
		margin: 0;
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
