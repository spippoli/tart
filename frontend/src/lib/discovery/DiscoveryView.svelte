<script lang="ts">
	import { onMount, type Snippet } from 'svelte';
	import { page } from '$app/state';
	import { currentUrl } from './url';
	import { m } from '#lib/paraglide/messages.js';
	import { getLocale, localizeHref } from '#lib/paraglide/runtime.js';
	import { vocabularyLabels } from '#lib/archive/records.ts';
	import type { components } from '../api/schema';
	import { RECORD_MAP_ZOOM } from '#lib/map/record-maps.ts';
	import { supportsWebGL2 } from '#lib/map/webgl.ts';
	import type { DiscoveryData } from '#lib/server/discovery.ts';
	import AlsoMatching from './AlsoMatching.svelte';
	import { chipsOf, cleared } from './chips';
	import FilterForm from './FilterForm.svelte';
	import ListEntry from './ListEntry.svelte';
	import Pagination from './Pagination.svelte';
	import { jump, viewportOf, type ViewportListing } from './explore';
	import { filterCount, forOtherView, parseState, queryString } from './state';
	/**
	 * What Explore and Archive share (Discovery spec, Explore and Archive views): the
	 * filter bar, the active filters as chips, the "Also matching" box, the total in a
	 * polite live region, and the paginated list of entries. The Explore view puts its map
	 * above this and, with a map, restricts the list to the viewport.
	 */
	let {
		data,
		view,
		heading,
		map,
		viewport = null,
		backToMap = false,
		listHidden = false
	}: {
		data: DiscoveryData;
		view: 'explore' | 'archive';
		heading: string;
		/** The map of Explore, between the filter bar and the list. */
		map?: Snippet;
		viewport?: ViewportListing | null;
		/** Offer "Back to the map" before the list (a wide screen with a map). */
		backToMap?: boolean;
		/** On a narrow screen the map is showing instead of the list. */
		listHidden?: boolean;
	} = $props();
	const locale = getLocale();

	const { state: loaded } = $derived(data);
	// The URL holds what the page changed since it loaded: the viewport and the selection.
	const filters = $derived(
		view === 'explore' ? parseState(new URLSearchParams(currentUrl().search), locale) : loaded
	);
	const results = $derived(viewport?.results ?? data.results);
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
	const count = $derived(new Intl.NumberFormat(locale).format(results.total));
	const total = $derived(
		viewport
			? results.total === 1
				? m.discovery_area_results_one({ page: results.page, pages })
				: m.discovery_area_results_other({ count, page: results.page, pages })
			: results.total === 1
				? m.discovery_results_one({ page: results.page, pages })
				: m.discovery_results_other({ count, page: results.page, pages })
	);

	// "Show on map" in the Archive view is a link to Explore; without WebGL2 there is no map.
	let canShowOnMap = $state(false);
	onMount(() => (canShowOnMap = view === 'archive' && supportsWebGL2()));
	/** Explore with the Location selected and the map on it, as the mini-map's link is. */
	function mapHref(entry: components['schemas']['ListEntry']) {
		const point = entry.location_point;
		return (
			localizeHref('/') +
			queryString(
				{
					...forOtherView(filters),
					location: entry.location,
					viewport: point ? viewportOf(RECORD_MAP_ZOOM, point) : null
				},
				locale
			)
		);
	}
	const wholeArchive = $derived(data.results.total);
</script>

{#if data.emptyArchive}
	<p class="band">
		{m.discovery_empty_archive()}
		<a href={localizeHref('/contribute')}>{m.discovery_empty_archive_link()}</a>
	</p>
{:else}
	<section class="bar" aria-label={m.discovery_filters()}>
		<FilterForm
			filters={loaded}
			expressionTypes={data.expressionTypes}
			areas={data.areas}
			keep={['artist', 'series']}
		/>
	</section>

	<div class="split" class:with-map={!!map}>
		{#if map}{@render map()}{/if}

		<div class="listing" hidden={listHidden}>
			<AlsoMatching also={data.results.also_matching} query={filters.q} />

			{#if (filters.createdFrom !== null || filters.createdTo !== null) && data.results.left_out > 0}
				<p class="notice">
					{data.results.left_out === 1
						? m.discovery_left_out_one()
						: m.discovery_left_out_other({ count: data.results.left_out })}
				</p>
			{/if}

			<section
				class="results"
				id="explore-list"
				tabindex="-1"
				aria-labelledby="results-heading"
				aria-busy={viewport?.busy || undefined}
			>
				{#if backToMap}
					<p>
						<a href="#explore-map" onclick={(event) => jump(event, 'explore-map')}
							>{m.discovery_back_to_map()}</a
						>
					</p>
				{/if}
				<h2 id="results-heading">{heading}</h2>
				<p class="total" role="status" aria-live="polite">{viewport?.failed ? '' : total}</p>
				{#if viewport?.updating}
					<p class="total" role="status">{m.discovery_updating()}</p>
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

				{#if viewport?.failed}
					<div class="empty" role="group">
						<p>{m.discovery_load_failed()}</p>
						<button type="button" onclick={viewport.onretry}>{m.discovery_retry()}</button>
					</div>
				{:else}
					{#if results.total === 0 && viewport && wholeArchive > 0}
						<div class="empty">
							<p>
								{wholeArchive === 1
									? m.discovery_empty_viewport_one()
									: m.discovery_empty_viewport_other({
											count: new Intl.NumberFormat(locale).format(wholeArchive)
										})}
							</p>
							<p class="actions">
								<button type="button" onclick={viewport.onwiden}>{m.discovery_widen()}</button>
								<a href={localizeHref('/archive') + queryString(forOtherView(filters), locale)}
									>{m.discovery_open_archive()}</a
								>
							</p>
						</div>
					{:else if results.total === 0}
						<p class="empty">{m.discovery_empty_none()}</p>
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
									<ListEntry {entry} selected={viewport?.selected === entry.location}>
										{#snippet onmap(title)}
											{#if viewport}
												<button
													type="button"
													class="show-on-map"
													aria-label={m.discovery_entry_show_on_map({ title })}
													data-entry={entry.id}
													onclick={() => viewport.onshow(entry)}
													>{m.discovery_entry_show_on_map_visible()}</button
												>
											{:else if canShowOnMap}
												<a
													class="show-on-map"
													href={mapHref(entry)}
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
						onpage={viewport?.onpage}
					/>
				{/if}
			</section>
		</div>
	</div>
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
	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem 1rem;
		align-items: center;
	}
	.show-on-map {
		justify-self: start;
	}
	/* The list beside the map on a wide screen; one under the other on a narrow one. */
	@media (min-width: 60.0625rem) {
		.split.with-map {
			display: grid;
			grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
			gap: 1rem;
			align-items: start;
		}
	}
	.list {
		display: grid;
		gap: 0.75rem;
		margin: 0;
		padding: 0;
		list-style: none;
	}
</style>
