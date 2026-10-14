<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import type { Bounds } from '#lib/map/bounds.ts';
	import type { View } from '#lib/map/engine.ts';
	import type { MapData } from '#lib/map/locations.ts';
	import Map from '#lib/map/Map.svelte';
	import { extentOf, locationFeature, RECORD_MAP_ZOOM } from '#lib/map/record-maps.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { recordHref, type PlaceView } from './records';

	/**
	 * The map of a Site, Area, or Series page (Discovery spec, Mini-map siblings; archive
	 * records, Other record pages): only the Locations of the place's public Artworks,
	 * framed on their extent and never past z17, and an Area's outline (a Series has
	 * none). Activating a Location opens its page. A place with nothing to draw has no
	 * map, and neither does a browser without JavaScript or WebGL2: the page lists its
	 * Locations in words.
	 */
	let { place }: { place: PlaceView } = $props();

	const settings = page.data.map as
		{ view: View; boundary: Bounds; attribution: { text: string; url: string }[] } | undefined;
	const outline = $derived(
		place.kind === 'area' && place.geometry?.type === 'Polygon'
			? (place.geometry as unknown as { type: 'Polygon'; coordinates: number[][][] })
			: null
	);
	const features = $derived(
		place.locations.flatMap((location) => locationFeature(location, location) ?? [])
	);
	const data = $derived<MapData>({ locations: features, sites: [], areas: [] });
	const bounds = $derived(
		extentOf([...features.map(({ geometry }) => geometry), ...(outline ? [outline] : [])])
	);
	const paths = $derived(new globalThis.Map(place.locations.map(({ id, path }) => [id, path])));

	function openLocation(id: number) {
		// The href is a localized record path already (no base path is configured).
		// eslint-disable-next-line svelte/no-navigation-without-resolve
		goto(recordHref('location', paths.get(id) ?? String(id)));
	}

	let shown = $state(false);
	onMount(() => (shown = true));
</script>

{#if shown && settings && bounds}
	<section class="place-map" aria-label={m.map_region()}>
		<Map
			view={settings.view}
			boundary={settings.boundary}
			attribution={settings.attribution}
			{data}
			{outline}
			frame={{ bounds, maxZoom: RECORD_MAP_ZOOM }}
			onselect={openLocation}
			onunavailable={() => (shown = false)}
		/>
	</section>
{/if}

<style>
	.place-map {
		margin-block: 1rem;
	}
</style>
