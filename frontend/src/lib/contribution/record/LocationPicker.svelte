<script lang="ts">
	import { vocabularyLabels } from '#lib/archive/records.ts';
	import type { LocationOption } from '#lib/map/LocationEntry.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import type { Locale } from '#lib/paraglide/runtime.js';
	import { findLocations } from '../find-locations';
	import type { PickedLocation } from './form';

	/**
	 * Picks an existing Location by a text (the Artworks on it, its Site, or its Area).
	 * Used to correct the Location of an Artwork, and the Location of the documentation of a
	 * disappearance; a Location is never made here.
	 */
	let {
		id,
		value = $bindable(),
		locale,
		surfaceTypes
	}: {
		id: string;
		value: PickedLocation | null;
		locale: Locale;
		surfaceTypes: { key: string; label: Record<string, string> }[];
	} = $props();

	let query = $state('');
	let results = $state<LocationOption[] | null>(null);
	const surfaceLabel = $derived(vocabularyLabels(surfaceTypes, locale));

	async function search() {
		results = await findLocations({ text: query }, surfaceLabel, locale);
	}

	function choose(option: LocationOption) {
		value = { id: Number(option.id), title: option.title };
		results = null;
		query = '';
	}
</script>

<div class="picker" {id} tabindex="-1">
	{#if value}
		<p>
			{m.editor_location_existing({ title: value.title })}
			<button type="button" onclick={() => (value = null)}>{m.location_entry_clear()}</button>
		</p>
	{/if}
	<label for="{id}-search">{m.location_entry_search_label()}</label>
	<div class="row">
		<input
			id="{id}-search"
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
		<button type="button" onclick={search}>{m.location_entry_search()}</button>
	</div>
	<div role="status">
		{#if results}
			{#if results.length === 0}
				<p>{m.location_entry_no_results()}</p>
			{:else}
				<ul aria-label={m.location_entry_results()}>
					{#each results as option (option.id)}
						<li>
							<button
								type="button"
								aria-label={m.location_entry_choose({ title: option.title })}
								onclick={() => choose(option)}
							>
								{option.title}
							</button>
							{#if option.description}<span>{option.description}</span>{/if}
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

	p {
		margin: 0;
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
