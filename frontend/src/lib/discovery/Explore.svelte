<script lang="ts">
	import { onMount, tick, untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { m } from '#lib/paraglide/messages.js';
	import { getLocale } from '#lib/paraglide/runtime.js';
	import { recordHref } from '#lib/archive/records.ts';
	import { fetchMapData } from '#lib/map/data.ts';
	import { EMPTY_MAP_DATA, type MapData } from '#lib/map/locations.ts';
	import type { Camera } from '#lib/map/engine.ts';
	import type { Point } from '#lib/map/coordinates.ts';
	import Map from '#lib/map/Map.svelte';
	import { extentOf } from '#lib/map/record-maps.ts';
	import type { Unavailable } from '#lib/map/style.ts';
	import { supportsWebGL2 } from '#lib/map/webgl.ts';
	import type { DiscoveryData } from '#lib/server/discovery.ts';
	import type { mapSettings } from '#lib/server/map-settings.ts';
	import type { components } from '../api/schema';
	import { cleared } from './chips';
	import DiscoveryView from './DiscoveryView.svelte';
	import {
		bboxParam,
		central,
		clampTo,
		contains,
		countsOf,
		extentOfSigns,
		FIT_MAX_ZOOM,
		jump,
		POSITION_ZOOM,
		viewOf,
		viewportOf,
		withSelection,
		type ViewportListing
	} from './explore';
	import LocationPanel from './LocationPanel.svelte';
	import { apiQuery, filterCount, parseState, queryString } from './state';
	import { currentUrl, shallow } from './url';

	/**
	 * Explore (Discovery spec, Explore and Archive views, Map/list sync, Selection and the
	 * side panel): the filter bar, the map, and the list of the Artworks of the Locations
	 * in the viewport. A selection and the viewport live in the URL (`?superficie=`
	 * and `?mappa=`). Without WebGL2, or when the map's style or tiles fail, it is the
	 * Archive view in place, with a notice; without JavaScript it is the list, rendered
	 * by the server.
	 */
	let { data }: { data: DiscoveryData & ReturnType<typeof mapSettings> } = $props();
	const locale = getLocale();

	type ArtworkPage = components['schemas']['ArtworkPage'];
	type Entry = components['schemas']['ListEntry'];
	type PanelBody = components['schemas']['LocationPanel'];

	// What the URL holds now: the selection and the viewport change without a load.
	const live = $derived(parseState(new URLSearchParams(currentUrl().search), locale));
	const selectedId = $derived(live.location);
	const path = $derived(currentUrl().pathname);
	/** The filters in the API's own parameters (no page, selection, or viewport). */
	const filterQuery = $derived(apiQuery({ ...data.state, page: 1 }).toString());

	// Whether there is a map: only with JavaScript and WebGL2, a style that loads, and tiles.
	let probed = $state(false);
	let unavailable = $state<Unavailable | null>(null);
	const showMap = $derived(probed && unavailable === null && !data.emptyArchive);
	let narrow = $state(false);
	let view = $state<'map' | 'list'>('map');
	onMount(() => {
		if (supportsWebGL2()) probed = true;
		else unavailable = 'webgl2';
		const query = matchMedia('(max-width: 60rem)');
		narrow = query.matches;
		const follow = () => (narrow = query.matches);
		query.addEventListener('change', follow);
		return () => query.removeEventListener('change', follow);
	});

	let map = $state<ReturnType<typeof Map>>();
	let mapReady = $state(false);
	let camera = $state<Camera | null>(null);

	// --- The Locations on the map ---------------------------------------------------------
	let mapData = $state<MapData>(EMPTY_MAP_DATA);
	let mapStatus = $state<'loading' | 'ready' | 'failed'>('loading');
	let mapRequest: AbortController | undefined;

	async function loadMap() {
		mapRequest?.abort();
		const request = (mapRequest = new AbortController());
		const result = await fetchMapData(
			filterQuery,
			(segment) => recordHref('site', segment),
			fetch,
			request.signal
		);
		if (request.signal.aborted) return;
		if ('failed' in result) {
			mapData = EMPTY_MAP_DATA;
			mapStatus = 'failed';
		} else {
			mapData = result.data;
			mapStatus = 'ready';
		}
	}

	$effect(() => {
		if (!showMap) return;
		void filterQuery;
		untrack(loadMap);
	});

	// --- The list of the viewport ---------------------------------------------------------
	let results = $state<ArtworkPage | null>(null);
	let failed = $state(false);
	let busy = $state(false);
	let updating = $state(false);
	let listRequest: AbortController | undefined;

	/** Fetches a page of the Artworks of the Locations in the viewport. */
	async function loadList(number: number) {
		if (!camera) return;
		listRequest?.abort();
		const request = (listRequest = new AbortController());
		busy = true;
		// "Updating results…" only if it takes more than 300 ms.
		const slow = setTimeout(() => (updating = true), 300);
		const query = apiQuery({ ...data.state, page: number });
		query.set('bbox', bboxParam(camera.bounds));
		try {
			const response = await fetch(`/api/discovery/artworks?${query}`, {
				headers: { accept: 'application/json' },
				signal: request.signal
			});
			if (!response.ok) throw new Error(String(response.status));
			const body = (await response.json()) as ArtworkPage;
			if (request.signal.aborted) return;
			results = body;
			failed = false;
		} catch {
			if (request.signal.aborted) return;
			results = null;
			failed = true;
		} finally {
			clearTimeout(slow);
			if (!request.signal.aborted) {
				busy = false;
				updating = false;
			}
		}
	}

	// A change of the filters or of the viewport resets the list to its first page.
	// The key is a string, so a camera that moved without changing the rounded bounds does not
	// rerun the effect; a burst of moves is answered once, after the map settles.
	const listKey = $derived(camera ? `${filterQuery}|${bboxParam(camera.bounds)}` : null);
	const LIST_DEBOUNCE_MS = 250;
	$effect(() => {
		if (!showMap || listKey === null) return;
		const first = untrack(() => results === null && !failed && !busy);
		if (first) {
			untrack(() => loadList(1));
			return;
		}
		const timer = setTimeout(() => loadList(1), LIST_DEBOUNCE_MS);
		return () => clearTimeout(timer);
	});

	function retry() {
		loadMap();
		loadList(1);
	}

	// --- Where the map is -----------------------------------------------------------------
	const start = $derived(data.state.viewport ? viewOf(data.state.viewport) : undefined);

	function moved(next: Camera) {
		// A map hidden by the switch has no size to report.
		if (narrow && view === 'list') return;
		camera = next;
		// The first camera is where the map starts, not a move.
		if (!mapReady) return;
		const viewport = viewportOf(next.zoom, next.center);
		shallow(path + queryString({ ...live, viewport }, locale), {
			replace: true,
			state: page.state
		});
	}

	/** The map fitted to the results, clamped to the Instance boundary. */
	function fitToResults() {
		const extent = extentOfSigns(mapData.locations);
		const clamped = extent && clampTo(extent, data.map.boundary);
		if (clamped) map?.fitTo(clamped, FIT_MAX_ZOOM);
	}

	/** "Widen the view": on a narrow screen the map comes forward first. */
	async function widen() {
		if (narrow && view === 'list') {
			view = 'map';
			await tick();
		}
		fitToResults();
	}

	// A URL with filters but no viewport opens fitted to the results.
	let opened = false;
	$effect(() => {
		if (!mapReady || mapStatus === 'loading' || opened) return;
		opened = true;
		untrack(() => {
			if (!data.state.viewport && filterCount(data.state) > 0) fitToResults();
		});
	});

	// Selecting Areas fits the map to their extent; no other filter moves it.
	let areas = untrack(() => data.state.area.join(','));
	$effect(() => {
		const chosen = data.state.area;
		const key = chosen.join(',');
		if (key === areas) return;
		areas = key;
		if (chosen.length > 0 && untrack(() => mapReady)) untrack(() => fitToAreas(chosen));
	});

	async function fitToAreas(ids: number[]) {
		const shapes = await Promise.all(
			ids.map(async (id) => {
				const response = await fetch(`/api/archive/areas/${id}`).catch(() => null);
				if (!response?.ok) return null;
				return ((await response.json()) as { geometry?: { type: string; coordinates: unknown } })
					.geometry;
			})
		);
		const extent = extentOf(shapes.filter((shape) => shape != null));
		const clamped = extent && clampTo(extent, data.map.boundary);
		if (clamped) map?.fitTo(clamped, FIT_MAX_ZOOM);
	}

	// --- Selection and the side panel -----------------------------------------------------
	type Opener = { kind: 'sign'; id: number } | { kind: 'button'; entry: number } | null;
	let opener: Opener = null;
	let focusTitle = false;
	let title = $state<HTMLElement>();
	let panel = $state<{
		id: number;
		status: 'loading' | 'ready' | 'failed';
		body: PanelBody | null;
	} | null>(null);
	let missing = $state(false);
	let panelRequest: AbortController | undefined;

	async function loadPanel(id: number) {
		panelRequest?.abort();
		const request = (panelRequest = new AbortController());
		panel = { id, status: 'loading', body: panel?.id === id ? panel.body : null };
		try {
			const response = await fetch(`/api/discovery/locations/${id}?${filterQuery}`, {
				headers: { accept: 'application/json' },
				signal: request.signal
			});
			if (request.signal.aborted) return;
			if (response.status === 404) {
				// A withdrawn and a missing Location read the same: nothing is selected.
				panel = null;
				missing = true;
				shallow(path + queryString({ ...live, location: null }, locale), {
					replace: true,
					state: page.state
				});
				return;
			}
			if (!response.ok) throw new Error(String(response.status));
			panel = { id, status: 'ready', body: (await response.json()) as PanelBody };
		} catch {
			if (!request.signal.aborted) panel = { id, status: 'failed', body: null };
		}
	}

	$effect(() => {
		const id = selectedId;
		if (!showMap || id === null) {
			panel = null;
			return;
		}
		void filterQuery;
		untrack(() => loadPanel(id));
	});

	$effect(() => {
		if (selectedId === null || !focusTitle) return;
		focusTitle = false;
		tick().then(() => title?.focus());
	});

	function select(id: number, from: Opener) {
		opener = from;
		focusTitle = true;
		missing = false;
		const url = path + queryString({ ...live, location: id }, locale);
		// A new selection is one step of history, so that Back closes it; moving to another
		// sign replaces it.
		if (selectedId === null) shallow(url, { replace: false, state: { opened: true } });
		else shallow(url, { replace: true, state: page.state });
	}

	async function close() {
		const from = opener;
		opener = null;
		if (page.state.opened) history.back();
		else {
			shallow(path + queryString({ ...live, location: null }, locale), {
				replace: true,
				state: page.state
			});
		}
		if (from?.kind === 'sign') {
			if (!map?.focusSign(from.id)) document.getElementById('explore-map')?.focus();
		} else if (from?.kind === 'button') {
			// On a narrow screen the list was hidden to show the map.
			if (narrow && view === 'map') {
				view = 'list';
				await tick();
			}
			document.querySelector<HTMLElement>(`[data-entry="${from.entry}"]`)?.focus();
		}
	}

	function onkeydown(event: KeyboardEvent) {
		if (event.key !== 'Escape' || selectedId === null || event.defaultPrevented) return;
		if ((event.target as Element | null)?.closest?.('dialog[open]')) return;
		close();
	}

	async function show(entry: Entry) {
		if (narrow && view === 'list') {
			view = 'map';
			await tick();
		}
		select(entry.location, { kind: 'button', entry: entry.id });
		const point = entry.location_point;
		if (point && (!camera || !central(camera.bounds, point))) map?.centerOn(point);
	}

	function clearFilters() {
		// eslint-disable-next-line svelte/no-navigation-without-resolve
		goto(path + queryString(cleared(live), locale), {
			replace: true,
			reset: false
		});
	}

	// The sign of a selection that no Artwork matching the filters stands behind.
	const shown = $derived.by(() => {
		if (failed) return EMPTY_MAP_DATA;
		const found = panel?.status === 'ready' && panel.id === selectedId ? panel.body : null;
		return found ? withSelection(mapData, found.location, countsOf(found.entries)) : mapData;
	});

	// --- "Centre on my position" ----------------------------------------------------------
	let positionNotice = $state<string | null>(null);

	function locate() {
		positionNotice = null;
		if (!navigator.geolocation) {
			positionNotice = m.map_position_failed();
			return;
		}
		// The position goes to the map and nowhere else: no request carries it.
		navigator.geolocation.getCurrentPosition(
			({ coords }) => {
				const point: Point = [coords.longitude, coords.latitude];
				if (!contains(data.map.boundary, point)) {
					positionNotice = m.map_position_outside();
					return;
				}
				map?.showPosition(point);
				map?.flyTo(point, POSITION_ZOOM);
			},
			(error) => {
				positionNotice =
					error.code === error.PERMISSION_DENIED
						? m.map_position_denied()
						: m.map_position_failed();
			}
		);
	}

	// --- What DiscoveryView shows ---------------------------------------------------------
	const listing = $derived<ViewportListing | null>(
		showMap && camera && (results || failed)
			? {
					results,
					failed,
					busy,
					updating,
					selected: selectedId,
					onpage: (number) => loadList(number),
					onretry: retry,
					onwiden: widen,
					onshow: show
				}
			: null
	);
	const count = $derived(listing?.results?.total ?? data.results.total);
	const wide = $derived(!narrow);
</script>

<svelte:window {onkeydown} />

{#if unavailable}
	<p class="notice">
		{unavailable === 'webgl2' ? m.discovery_webgl_notice() : m.discovery_map_off_notice()}
		{#if unavailable === 'webgl2'}
			<a href="#map-help" onclick={(event) => jump(event, 'map-help')}>{m.discovery_webgl_why()}</a>
		{/if}
	</p>
	{#if live.location !== null}
		<p class="notice">
			{m.discovery_selection_link()}
			<a href={recordHref('location', String(live.location))}>{m.discovery_selection_link_open()}</a
			>
		</p>
	{/if}
{/if}

{#if missing}
	<p class="notice" role="status">{m.discovery_unavailable_place()}</p>
{/if}

{#snippet mapRegion()}
	{#if showMap}
		<section
			class="explore-map"
			id="explore-map"
			tabindex="-1"
			aria-label={m.map_region()}
			hidden={narrow && view === 'list'}
		>
			{#if wide}
				<a class="skip" href="#explore-list" onclick={(event) => jump(event, 'explore-list')}>
					{count === 1
						? m.discovery_skip_map_one()
						: m.discovery_skip_map_other({ count: new Intl.NumberFormat(locale).format(count) })}
				</a>
			{/if}
			<Map
				bind:this={map}
				view={data.map.view}
				{start}
				boundary={data.map.boundary}
				attribution={data.map.attribution}
				data={shown}
				onselect={(id) => select(id, { kind: 'sign', id })}
				onunavailable={(reason) => (unavailable = reason)}
				onmoveend={moved}
				onready={() => (mapReady = true)}
				onlocate={locate}
			>
				<div class="status" role="status" aria-live="polite">
					{#if mapStatus === 'loading'}
						{m.map_locations_loading()}
					{:else if mapStatus === 'failed' && !failed}
						{m.map_locations_failed()}
					{/if}
					{#if positionNotice}{positionNotice}{/if}
				</div>
				{#if mapStatus === 'failed' && !failed}
					<button type="button" onclick={loadMap}>{m.map_retry()}</button>
				{/if}
			</Map>
			{#if selectedId !== null && !(narrow && view === 'list')}
				<div class="sheet">
					<LocationPanel
						bind:title
						status={panel?.status ?? 'loading'}
						panel={panel?.body ?? null}
						onclose={close}
						onclear={clearFilters}
						onretry={() => loadPanel(selectedId)}
					/>
				</div>
			{/if}
		</section>
	{/if}
{/snippet}

{#if showMap && narrow}
	<div class="switch" role="group" aria-label={m.discovery_view_label()}>
		<button type="button" aria-pressed={view === 'map'} onclick={() => (view = 'map')}
			>{m.discovery_view_map()}</button
		>
		<button type="button" aria-pressed={view === 'list'} onclick={() => (view = 'list')}
			>{m.discovery_view_list()}</button
		>
	</div>
{/if}

<DiscoveryView
	{data}
	view="explore"
	heading={m.discovery_list_label()}
	map={showMap ? mapRegion : undefined}
	viewport={listing}
	backToMap={showMap && wide}
	listHidden={showMap && narrow && view === 'map'}
/>

{#if unavailable === 'webgl2'}
	<div id="map-help" tabindex="-1">
		<h2>{m.discovery_webgl_help_heading()}</h2>
		<ul>
			<li>{m.discovery_webgl_help_acceleration()}</li>
			<li>{m.discovery_webgl_help_update()}</li>
		</ul>
	</div>
{/if}

<style>
	.notice {
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--border);
		border-radius: 4px;
		background: var(--surface);
	}
	.explore-map {
		position: relative;
	}
	.explore-map[hidden] {
		display: none;
	}
	.skip:not(:focus) {
		position: absolute;
		inline-size: 1px;
		block-size: 1px;
		overflow: hidden;
		clip-path: inset(50%);
	}
	.skip:focus {
		display: block;
		padding: 0.5rem;
		background: var(--background);
	}
	.status {
		padding-inline: 0.25rem;
		background: var(--background);
	}
	.status:empty {
		display: none;
	}
	.switch {
		display: flex;
		gap: 0.5rem;
		margin-block: 0.5rem;
	}
	.switch button {
		flex: 1;
		min-block-size: 2.75rem;
	}
	.switch button[aria-pressed='true'] {
		font-weight: 700;
		border-block-end: 4px solid var(--accent);
	}
	/* The side panel overlays the map's right side; the bottom sheet rises from the screen's edge. */
	.sheet {
		position: absolute;
		z-index: 3;
		inset-block: 0.5rem 2.5rem;
		inset-inline-end: 0.5rem;
		inline-size: min(24rem, calc(100% - 1rem));
		display: grid;
		grid-template-rows: minmax(0, 1fr);
	}
	@media (max-width: 60rem) {
		.sheet {
			position: fixed;
			inset: auto 0 0 0;
			inline-size: auto;
			max-block-size: 60vh;
			z-index: 10;
		}
	}
	#map-help {
		margin-block: 1rem;
	}
</style>
