<script lang="ts">
	import { page } from '$app/state';
	import { m } from '#lib/paraglide/messages.js';
	import { localizeHref } from '#lib/paraglide/runtime.js';
	import type { Bounds } from './bounds';
	import type { View } from './engine';
	import type { MapData } from './locations';
	import Map from './Map.svelte';
	import {
		exploreHref,
		extentOf,
		locationFeature,
		RECORD_MAP_ZOOM,
		type Counts,
		type PlainLocation
	} from './record-maps';

	/**
	 * The mini-map of an Artwork or Location page (Discovery spec, Mini-map): the
	 * record's Location at z17, or at its extent if larger, highlighted; the public
	 * Locations within 500 m muted around it. It is still (no wheel or drag), has only
	 * the zoom buttons, goes no lower than z15, and links to Explore on that Location.
	 */
	let {
		location,
		counts,
		nearby,
		onready,
		onunavailable
	}: {
		location: PlainLocation;
		/** The Artworks on the Location by Condition group: the sign it is drawn with. */
		counts: Partial<Counts>;
		nearby: readonly { id: number; point: [number, number] }[];
		onready: () => void;
		onunavailable: () => void;
	} = $props();

	const settings = page.data.map as {
		view: View;
		boundary: Bounds;
		attribution: { text: string; url: string }[];
	};
	let ready = $state(false);
	const feature = $derived(locationFeature(location, counts));
	const data = $derived<MapData>({ locations: feature ? [feature] : [], sites: [], areas: [] });
	const bounds = $derived(location.geometry ? extentOf([location.geometry as never]) : null);
	const href = $derived(
		feature &&
			exploreHref(
				localizeHref('/'),
				{ selection: m.query_key_selection(), viewport: m.query_key_viewport() },
				location.id,
				feature.properties.point,
				RECORD_MAP_ZOOM
			)
	);
</script>

{#if bounds}
	<div class="mini-map">
		<Map
			mini
			view={settings.view}
			boundary={settings.boundary}
			attribution={settings.attribution}
			{data}
			frame={{ bounds, maxZoom: RECORD_MAP_ZOOM }}
			muted={nearby.map(({ point }) => point)}
			onready={() => {
				ready = true;
				onready();
			}}
			{onunavailable}
		/>
		{#if href && ready}<p><a {href}>{m.map_open_on_map()}</a></p>{/if}
	</div>
{/if}

<style>
	.mini-map p {
		margin-block: 0.5rem 0;
	}
</style>
