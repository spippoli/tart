<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import * as api from './api';

	/**
	 * Picks an Artwork of the archive by a text: search, then use one. Used where a record
	 * links to an Artwork that exists (the covering Artwork of a History event, the Artworks
	 * a Documentation item is about).
	 */
	let {
		id,
		label,
		onpick
	}: {
		id: string;
		label: string;
		onpick: (artwork: { id: number; title: string }) => void;
	} = $props();

	let query = $state('');
	let results = $state<{ id: number; title: string }[] | null>(null);
	let failed = $state(false);

	async function search() {
		const text = query.trim();
		if (text.length < 2) return;
		const found = await api.searchArtworks(text);
		failed = !found.ok;
		results = found.ok
			? found.value.entries.map((entry) => ({
					id: entry.id,
					title: entry.title ?? m.archive_untitled()
				}))
			: null;
	}

	function use(artwork: { id: number; title: string }) {
		results = null;
		query = '';
		onpick(artwork);
	}
</script>

<div class="picker">
	<label for={id}>{label}</label>
	<div class="row">
		<input
			{id}
			type="search"
			autocomplete="off"
			bind:value={query}
			onkeydown={(event) => {
				if (event.key === 'Enter') {
					event.preventDefault();
					void search();
				}
			}}
		/>
		<button type="button" onclick={search}>{m.editor_picker_search()}</button>
	</div>
	<div role="status">
		{#if failed}
			<p>{m.editor_picker_failed()}</p>
		{:else if results}
			{#if results.length === 0}
				<p>{m.editor_picker_none()}</p>
			{:else}
				<ul aria-label={m.editor_picker_results()}>
					{#each results as artwork (artwork.id)}
						<li>
							{artwork.title}
							<button type="button" onclick={() => use(artwork)}>
								{m.editor_picker_use({ name: artwork.title })}
							</button>
						</li>
					{/each}
				</ul>
			{/if}
		{/if}
	</div>
</div>

<style>
	.picker {
		display: grid;
		gap: 0.5rem;
		justify-items: start;
	}

	label {
		font-weight: 600;
	}

	.row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	ul {
		margin: 0;
		padding-inline-start: 1.25rem;
		display: grid;
		gap: 0.5rem;
	}

	p {
		margin: 0;
	}

	input,
	button {
		min-block-size: 2.75rem;
		padding-inline: 0.75rem;
		background: var(--background);
		color: var(--text);
		border: 1px solid var(--border);
	}

	button {
		cursor: pointer;
	}
</style>
