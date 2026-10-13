<script lang="ts">
	import LinkList from './LinkList.svelte';
	import type { components } from '../api/schema';
	import { m } from '#lib/paraglide/messages.js';
	import { archiveContext } from './context.svelte';
	import { geoUri, representativePoint } from './geometry';
	import RecordAnchor from './RecordAnchor.svelte';
	import { locationTitleText, recordHref } from './records';

	/**
	 * Where an Artwork is, in words (archive-records spec, criterion 33): the Location,
	 * its Areas and Site, the approximate-location notice, the coordinates, and a `geo:`
	 * link. It stands in for the mini-map, which the Discovery spec adds, and stays as
	 * its fallback without WebGL2.
	 */
	let { where }: { where: components['schemas']['Where'] } = $props();
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
		{#if location.approximate}
			<p>
				{location.uncertainty_radius
					? m.archive_approximate_radius({ radius: String(location.uncertainty_radius) })
					: m.archive_approximate()}
			</p>
		{/if}
		{#if point}
			<p>
				{m.archive_coordinates({ latitude: point[1].toFixed(5), longitude: point[0].toFixed(5) })}
				· <a href={geoUri(point, location.uncertainty_radius)}>{m.archive_open_in_maps()}</a>
			</p>
		{/if}
		<p class="note">{m.archive_minimap_note()}</p>
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
