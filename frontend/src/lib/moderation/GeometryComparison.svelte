<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { formatNumber } from '#lib/i18n/format.ts';
	import type { Bounds } from '#lib/map/bounds.ts';
	import type { Point } from '#lib/map/coordinates.ts';
	import type { Drawn, View } from '#lib/map/engine.ts';
	import Map from '#lib/map/Map.svelte';
	import { extentOf } from '#lib/map/record-maps.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { localizeHref } from '#lib/paraglide/runtime.js';
	import type { components } from '../api/schema';
	import { directionText } from './words';

	type Comparison = components['schemas']['GeometryComparisonOut'];
	type GeoJson = { type: string; coordinates: unknown };

	/**
	 * One geometry against the one it replaces (Contribution and moderation spec, Submission
	 * page): a map with both overlaid, the current one grey with a solid outline and the
	 * proposed one with a dashed outline, a legend in words, and, below, a text summary of
	 * what changed. Without WebGL2 or JavaScript only the summary is shown, so it says it all.
	 */
	let { comparison, locale }: { comparison: Comparison; locale: string } = $props();

	const settings = page.data.map as
		{ view: View; boundary: Bounds; attribution: { text: string; url: string }[] } | undefined;
	const summary = $derived(comparison.summary);
	const current = $derived(comparison.current as GeoJson | null);
	const proposed = $derived(comparison.proposed as GeoJson);

	const outline = $derived(
		current?.type === 'Polygon'
			? (current as unknown as { type: 'Polygon'; coordinates: number[][][] })
			: null
	);

	function vertices(geometry: GeoJson): Point[] {
		switch (geometry.type) {
			case 'Point':
				return [geometry.coordinates as Point];
			case 'LineString':
				return geometry.coordinates as Point[];
			default:
				return (geometry.coordinates as Point[][])[0].slice(0, -1);
		}
	}

	/** The current point or line is drawn as muted marks: grey, and not the proposal's dashes. */
	const muted = $derived<Point[]>(current && !outline ? vertices(current) : []);
	const drawn = $derived<Drawn>({
		vertices: vertices(proposed),
		ring: proposed.type === 'Polygon',
		selected: null,
		midpoints: false
	});
	const bounds = $derived(extentOf([...(current ? [current] : []), proposed]));

	let shown = $state(false);
	onMount(() => (shown = true));

	const number = (value: number) => formatNumber(Math.abs(value), { locale });
</script>

<div class="geometry">
	{#if shown && settings && bounds}
		<div class="map" role="group" aria-label={m.moderation_geometry_map()}>
			<Map
				mini
				view={settings.view}
				boundary={settings.boundary}
				attribution={settings.attribution}
				{outline}
				{muted}
				{drawn}
				frame={{ bounds, maxZoom: 17 }}
				onunavailable={() => (shown = false)}
			/>
		</div>
		<h4>{m.moderation_geometry_legend()}</h4>
		<ul class="legend">
			{#if current}
				<li>{m.moderation_geometry_legend_current()}</li>
			{:else}
				<li>{m.moderation_geometry_legend_new()}</li>
			{/if}
			<li>{m.moderation_geometry_legend_proposed()}</li>
		</ul>
	{/if}

	<h4>{m.moderation_geometry_summary()}</h4>
	<ul class="summary">
		<li>
			{#if summary.vertices_before === null}
				{m.moderation_geometry_vertices_new({ after: summary.vertices_after })}
			{:else}
				{m.moderation_geometry_vertices({
					before: summary.vertices_before,
					after: summary.vertices_after
				})}
			{/if}
		</li>
		{#if summary.largest_shift_metres !== null}
			<li>
				{#if summary.shift_direction}
					{m.moderation_geometry_shift({
						metres: formatNumber(summary.largest_shift_metres, { locale }),
						direction: directionText(summary.shift_direction)
					})}
				{:else}
					{m.moderation_geometry_still()}
				{/if}
			</li>
		{/if}
		{#if summary.area_change_square_metres !== null}
			<li>
				{#if summary.area_change_square_metres >= 0}
					{m.moderation_geometry_surface_more({ area: number(summary.area_change_square_metres) })}
				{:else}
					{m.moderation_geometry_surface_less({ area: number(summary.area_change_square_metres) })}
				{/if}
			</li>
		{/if}
		{#if comparison.locations_entering !== null}
			<li>{m.moderation_geometry_entering({ count: comparison.locations_entering })}</li>
		{/if}
		{#if comparison.locations_leaving !== null}
			<li>{m.moderation_geometry_leaving({ count: comparison.locations_leaving })}</li>
		{/if}
		{#if comparison.record_kind === 'location'}
			<li>
				{#if comparison.near_locations.length === 0}
					{m.moderation_geometry_near_none()}
				{:else}
					{m.moderation_geometry_near()}
					<ul>
						{#each comparison.near_locations as near (near.id)}
							<li>
								<a href={localizeHref(`/locations/${near.id}`)}
									>{m.moderation_geometry_near_item({
										id: near.id,
										metres: formatNumber(near.distance_metres, { locale })
									})}</a
								>
							</li>
						{/each}
					</ul>
				{/if}
			</li>
		{/if}
	</ul>
</div>

<style>
	.geometry {
		max-inline-size: 50rem;
	}

	.map {
		margin-block: 0.5rem;
	}

	h4 {
		margin-block: 0.75rem 0.25rem;
	}

	.legend,
	.summary {
		margin-block: 0.25rem;
		padding-inline-start: 1.25rem;
	}
</style>
