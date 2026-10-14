<script lang="ts">
	import { onMount } from 'svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { localizeHref } from '#lib/paraglide/runtime.js';
	import { textDirection } from '#lib/i18n/language.ts';
	import { recordHref } from '#lib/archive/records.ts';
	import { fetchMapData } from '#lib/map/data.ts';
	import { EMPTY_MAP_DATA, type MapData } from '#lib/map/locations.ts';
	import Map from '#lib/map/Map.svelte';
	import PageTitle from '#lib/shell/PageTitle.svelte';
	import type { PageProps } from './$types';

	// The intro band and the map of Explore; the Discovery spec adds the filters and the list.
	let { data }: PageProps = $props();
	const language = $derived(data.contentLanguage);

	// The map exists only with JavaScript; without WebGL2, with a style that fails to
	// load, or without tiles, it is left out. The list that works without it comes
	// with the Explore view.
	let mapAvailable = $state(false);
	let mapData = $state<MapData>(EMPTY_MAP_DATA);
	onMount(() => {
		mapAvailable = true;
		fetchMapData().then((fetched) => {
			// The Site pages are named by their path in the UI language.
			mapData = {
				...fetched,
				sites: fetched.sites.map((site) => ({ ...site, path: recordHref('site', site.path) }))
			};
		});
	});
</script>

<PageTitle title={m.nav_explore()} />

<section class="intro">
	<h1 lang={language} dir={textDirection(language)}>{data.identity.name}</h1>
	<p class="prose" lang={language} dir={textDirection(language)}>{data.identity.description}</p>
	<p><a href={localizeHref('/about')}>{m.nav_about()}</a></p>
</section>

{#if mapAvailable}
	<section class="explore-map" aria-label={m.map_region()}>
		<Map
			view={data.map.view}
			boundary={data.map.boundary}
			attribution={data.map.attribution}
			data={mapData}
			onunavailable={() => (mapAvailable = false)}
		/>
	</section>
{/if}
