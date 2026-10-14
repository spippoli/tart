<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import MiniMap from '#lib/map/MiniMap.svelte';
	import type { Counts } from '#lib/map/record-maps.ts';
	import LinkList from './LinkList.svelte';
	import type { components } from '../api/schema';
	import { m } from '#lib/paraglide/messages.js';
	import { archiveContext } from './context.svelte';
	import { geoUri, representativePoint } from './geometry';
	import RecordAnchor from './RecordAnchor.svelte';
	import { locationTitleText, recordHref } from './records';

	/**
	 * Where an Artwork is: the mini-map (Discovery spec) with the Location, its Areas
	 * and Site, and the approximate-location notice. Without JavaScript, without WebGL2,
	 * or when the map cannot load, a text box takes the map's place (archive-records
	 * spec, criterion 33; Discovery spec, Mini-map): the same words, the coordinates,
	 * and a `geo:` link.
	 */
	let { where, counts = {} }: { where: components['schemas']['Where']; counts?: Partial<Counts> } =
		$props();
	let map = $state<'off' | 'loading' | 'ready'>('off');
	onMount(() => {
		if (page.data.map && where.location?.geometry) map = 'loading';
	});
	const context = archiveContext();
	const location = $derived(where.location);
	const point = $derived(
		location?.geometry ? representativePoint(location.geometry as never) : null
	);
</script>

<div class="where">
	{#if where.location_withdrawn || !location}
		<p>{m.archive_location_withdrawn()}</p>
	{:else}
		<dl>
			<dt>{m.archive_location()}</dt>
			<dd>
				<a
					href={recordHref('location', location.path)}
					lang={location.title.place_description ? context.contentLanguage : undefined}
					>{locationTitleText(location.id, location.title, context.surfaceType, context.locale)}</a
				>
				({context.surfaceType(location.surface_type)})
			</dd>
			{#if where.site}
				<dt>{m.archive_site()}</dt>
				<dd><RecordAnchor link={where.site} /></dd>
			{/if}
			{#if where.areas.length > 0}
				<dt>{m.archive_areas()}</dt>
				<dd>
					<LinkList links={where.areas} />
				</dd>
			{/if}
		</dl>
		{#if map !== 'off' && location.geometry}
			<MiniMap
				{location}
				{counts}
				nearby={where.nearby ?? []}
				onready={() => (map = 'ready')}
				onunavailable={() => (map = 'off')}
			/>
		{/if}
		{#if location.approximate}
			<p>
				{location.uncertainty_radius
					? m.archive_approximate_radius({ radius: String(location.uncertainty_radius) })
					: m.archive_approximate()}
			</p>
		{/if}
		{#if point && map !== 'ready'}
			<p>
				{m.archive_coordinates({ latitude: point[1].toFixed(5), longitude: point[0].toFixed(5) })}
				· <a href={geoUri(point, location.uncertainty_radius)}>{m.archive_open_in_maps()}</a>
			</p>
		{/if}
		{#if map === 'off'}<p class="note">{m.archive_minimap_note()}</p>{/if}
	{/if}
</div>

<style>
	.where {
		border: 1px solid var(--border);
		border-radius: 4px;
		padding: 0.75rem 1rem;
		background: var(--surface);
	}
	dl {
		display: grid;
		grid-template-columns: max-content 1fr;
		gap: 0.25rem 1rem;
		margin: 0;
	}
	dt {
		font-weight: 600;
	}
	dd {
		margin: 0;
	}
	.note {
		color: var(--text-muted);
		font-size: 0.9em;
		margin-block-end: 0;
	}
</style>
