<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { m } from '#lib/paraglide/messages.js';
	import { getLocale, localizeHref } from '#lib/paraglide/runtime.js';
	import { vocabularyLabels } from '#lib/archive/records.ts';
	import { supportsWebGL2 } from '#lib/map/webgl.ts';
	import type { DiscoveryData } from '#lib/server/discovery.ts';
	import AlsoMatching from './AlsoMatching.svelte';
	import { chipsOf, cleared } from './chips';
	import FilterForm from './FilterForm.svelte';
	import ListEntry from './ListEntry.svelte';
	import Pagination from './Pagination.svelte';
	import { filterCount, queryString } from './state';

	/**
	 * What Explore and Archive share (Discovery spec, Explore and Archive views): the
	 * filter bar, the active filters as chips, the "Also matching" box, the total in a
	 * polite live region, and the paginated list of entries. The Explore view puts its map
	 * above this and, with a map, restricts the list to the viewport.
	 */
	let {
		data,
		view,
		heading
	}: { data: DiscoveryData; view: 'explore' | 'archive'; heading: string } = $props();
	const locale = getLocale();

	const { state: filters, results } = $derived(data);
	const path = $derived(page.url.pathname);
	const pages = $derived(Math.max(1, Math.ceil(results.total / results.page_size)));
	const typeLabel = $derived(vocabularyLabels(data.expressionTypes, locale));
	const areaName = (id: number) => data.areas.find((area) => area.id === id)?.name ?? String(id);
	const chips = $derived(
		chipsOf(filters, {
			locale,
			type: typeLabel,
			area: areaName,
			artist: data.linked.artist,
			series: data.linked.series
		})
	);
	const active = $derived(filterCount(filters) > 0);
	const href = (next: typeof filters) => path + queryString(next, locale);
	const total = $derived(
		results.total === 1
			? m.discovery_results_one({ page: results.page, pages })
			: m.discovery_results_other({
					count: new Intl.NumberFormat(locale).format(results.total),
					page: results.page,
					pages
				})
	);

	// "Show on map" in the Archive view is a link to Explore; without WebGL2 there is no map.
	let canShowOnMap = $state(false);
	onMount(() => (canShowOnMap = view === 'archive' && supportsWebGL2()));
	const mapHref = (location: number) =>
		localizeHref('/') + queryString({ ...filters, location, page: 1 }, locale);
</script>

{#if data.emptyArchive}
	<p class="band">
		{m.discovery_empty_archive()}
		<a href={localizeHref('/contribute')}>{m.discovery_empty_archive_link()}</a>
	</p>
{:else}
	<section class="bar" aria-label={m.discovery_filters()}>
		<FilterForm
			{filters}
			expressionTypes={data.expressionTypes}
			areas={data.areas}
			keep={['artist', 'series']}
		/>
	</section>

	<AlsoMatching also={results.also_matching} query={filters.q} />

	{#if (filters.createdFrom !== null || filters.createdTo !== null) && results.left_out > 0}
		<p class="notice">
			{results.left_out === 1
				? m.discovery_left_out_one()
				: m.discovery_left_out_other({ count: results.left_out })}
		</p>
	{/if}

	<section class="results" aria-labelledby="results-heading">
		<h2 id="results-heading">{heading}</h2>
		<p class="total" role="status" aria-live="polite">{total}</p>

		{#if results.total === 0}
			<p class="empty">{m.discovery_empty_none()}</p>
		{/if}

		{#if active}
			<nav class="chips" aria-label={m.discovery_chips_label()}>
				<ul>
					{#each chips as chip (chip.id)}
						<li>
							<a href={href(chip.remaining)} aria-label={chip.removeLabel}
								>{chip.label} <span aria-hidden="true">×</span></a
							>
						</li>
					{/each}
				</ul>
				<a class="clear" href={href(cleared(filters))}>{m.discovery_clear_all()}</a>
			</nav>
		{/if}

		{#if results.total === 0 && filters.q && active}
			<p>
				<a href={href({ ...cleared(filters), q: filters.q })}>{m.discovery_search_whole()}</a>
			</p>
		{/if}

		{#if results.entries.length > 0}
			<ul class="list" aria-label={m.discovery_list_label()}>
				{#each results.entries as entry (entry.id)}
					<li>
						<ListEntry {entry}>
							{#snippet onmap(title)}
								{#if canShowOnMap}
									<a
										class="show-on-map"
										href={mapHref(entry.location)}
										aria-label={m.discovery_entry_show_on_map({ title })}
										>{m.discovery_entry_show_on_map_visible()}</a
									>
								{/if}
							{/snippet}
						</ListEntry>
					</li>
				{/each}
			</ul>
		{/if}

		<Pagination
			current={results.page}
			{pages}
			href={(number) => href({ ...filters, page: number })}
		/>
	</section>
{/if}

<style>
	.band,
	.notice,
	.empty {
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--border);
		border-radius: 4px;
		background: var(--surface);
	}
	.bar {
		margin-block: 1rem;
	}
	.total {
		color: var(--text-muted);
		margin-block: 0.25rem;
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem 1rem;
		margin-block: 0.75rem;
	}
	.chips ul {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.chips li a {
		display: inline-block;
		padding: 0.15rem 0.6rem;
		border: 1px solid var(--border);
		border-radius: 1rem;
		text-decoration: none;
		background: var(--surface);
	}
	.list {
		display: grid;
		gap: 0.75rem;
		margin: 0;
		padding: 0;
		list-style: none;
	}
</style>
