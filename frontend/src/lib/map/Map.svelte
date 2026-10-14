<script lang="ts">
	import { onMount } from 'svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { getLocale } from '#lib/paraglide/runtime.js';
	import { mapBounds, type Bounds } from './bounds';
	import type { AreaOutline, Camera, ClickEvent, Drawn, Engine, Frame, View } from './engine';
	import type { Point } from './coordinates';
	import Legend from './Legend.svelte';
	import { EMPTY_MAP_DATA, type MapData } from './locations';
	import MapControl from './MapControl.svelte';
	import { clusterName, signName } from './names';
	import { DARK_SCHEME, fetchStyle, type Theme, type Tokens, type Unavailable } from './style';
	import { supportsWebGL2 } from './webgl';

	/** The mini-map never zooms out past this, so its buttons stay within the loaded area. */
	const MINI_MIN_ZOOM = 15;

	/**
	 * The map module (Discovery spec, Modules): renders a map from the served style
	 * of the UI theme into its container, with the map control, the legend, and the
	 * attribution, kept within the boundary plus 2 km and below z19, and draws `data`:
	 * a sign per Location, clusters, geometries, and Site and Area labels. Each Location
	 * and cluster in view is also one focusable button; `onselect` gets a Location's id.
	 * It reports
	 * `onunavailable` without WebGL2, when the style fails to load, or when the tile
	 * extract is missing, and then renders nothing. The camera after each move is
	 * on the root's `data-*` attributes and given to `onmoveend`.
	 */
	let {
		view,
		boundary,
		attribution,
		data = EMPTY_MAP_DATA,
		onselect,
		onunavailable,
		onmoveend,
		onclick,
		drawn = null,
		frame,
		mini = false,
		muted = [],
		outline = null,
		onready
	}: {
		/** The Instance's default view, which the reset button returns to. */
		view: View;
		/** The bounding box of the Instance boundary. */
		boundary: Bounds;
		attribution: readonly { text: string; url: string }[];
		data?: MapData;
		onselect?: (id: number) => void;
		onunavailable: (reason: Unavailable) => void;
		onmoveend?: (camera: Camera) => void;
		/** Clicks on the map, for the drawing tool. */
		onclick?: (click: ClickEvent) => void;
		/** The shape being drawn, for the drawing tool. */
		drawn?: Drawn | null;
		/** Framed on an extent instead of the default view (a record page's map). */
		frame?: Frame;
		/**
		 * The mini-map (Discovery spec, Mini-map): still, with only the zoom buttons, no
		 * lower than z15, no clusters, no legend, and no focusable signs.
		 */
		mini?: boolean;
		/** The mini-map's neighbouring Locations, as small muted signs. */
		muted?: readonly Point[];
		/** An Area's outline. */
		outline?: AreaOutline | null;
		/** Called once the map is drawn. */
		onready?: () => void;
	} = $props();

	/** Moves the map so that `point` is at its centre. */
	export function centerOn(point: Point) {
		engine?.centerOn(point);
	}

	let container = $state<HTMLDivElement>();
	let engine = $state<Engine>();
	let tokens = $state<Tokens>();
	let unavailable = $state(false);
	let camera = $state<Camera>();

	$effect(() => {
		if (engine && tokens) engine.setDrawn(drawn, tokens);
	});

	$effect(() => {
		engine?.setMuted(muted);
	});

	$effect(() => {
		engine?.setOutline(outline);
	});

	onMount(() => {
		const scheme = matchMedia(DARK_SCHEME);
		const theme = (): Theme => (scheme.matches ? 'dark' : 'light');
		let gone = false;

		function fail(reason: Unavailable) {
			if (gone || unavailable) return;
			unavailable = true;
			engine?.destroy();
			engine = undefined;
			onunavailable(reason);
		}

		async function start() {
			if (!supportsWebGL2()) return fail('webgl2');
			const [{ createEngine }, result] = await Promise.all([
				import('./engine'),
				fetchStyle(theme())
			]);
			if (gone) return;
			if ('unavailable' in result) return fail(result.unavailable);
			tokens = result.style.metadata['tart:tokens'];
			try {
				const created = await createEngine(container!, {
					style: result.style,
					view,
					frame,
					minZoom: mini ? MINI_MIN_ZOOM : undefined,
					still: mini,
					bounds: mapBounds(boundary),
					attribution,
					labels: {
						canvas: mini ? m.map_canvas_mini() : m.map_canvas(),
						attributionToggle: m.map_attribution_toggle()
					},
					onClick: onclick && ((click) => onclick(click)),
					onMoveEnd(moved) {
						camera = moved;
						onmoveend?.(moved);
					},
					archive: {
						describe: {
							sign: (properties) => signName(properties, getLocale()),
							cluster: (artworks, locations) => clusterName(artworks, locations, getLocale())
						},
						onSelect: (id) => onselect?.(id),
						cluster: !mini,
						focusable: !mini
					}
				});
				if (gone) created.destroy();
				else {
					engine = created;
					onready?.();
				}
			} catch (reason) {
				fail(reason === 'webgl2' ? 'webgl2' : 'style');
			}
		}

		// The map follows the UI theme live (criterion 15).
		async function switchTheme() {
			const result = await fetchStyle(theme());
			if (gone || !engine) return;
			if ('unavailable' in result) return fail(result.unavailable);
			tokens = result.style.metadata['tart:tokens'];
			engine.setStyle(result.style);
		}

		start();
		scheme.addEventListener('change', switchTheme);
		return () => {
			gone = true;
			scheme.removeEventListener('change', switchTheme);
			engine?.destroy();
		};
	});

	$effect(() => {
		engine?.setData(data);
	});
</script>

{#if !unavailable}
	<div
		class="map"
		data-state={engine ? 'ready' : 'loading'}
		data-mini={mini || undefined}
		data-zoom={camera?.zoom}
		data-lon={camera?.center[0]}
		data-lat={camera?.center[1]}
		data-bearing={camera?.bearing}
		data-pitch={camera?.pitch}
		style:--map-ink={tokens?.['map.ink']}
		style:--map-paper={tokens?.['map.paper']}
	>
		<div class="overlay" role="group" aria-label={m.map_controls()}>
			{#if engine}
				<MapControl {engine} zoomOnly={mini} />
			{/if}
			{#if tokens && !mini}
				<Legend {tokens} />
			{/if}
		</div>
		<div class="canvas" bind:this={container}></div>
	</div>
{/if}

<style>
	/* The focusable elements over the canvas: a hit target of at least 24 × 24 px (WCAG 2.5.8). */
	.map :global(.tart-sign) {
		inline-size: 1.5rem;
		block-size: 1.5rem;
		padding: 0;
		background: transparent;
		border: 0;
		cursor: pointer;
	}

	.map :global(.tart-sign:focus-visible),
	.map :global(.tart-site:focus-visible) {
		outline: 3px solid var(--map-ink);
		outline-offset: 1px;
	}

	.map :global(.tart-site) {
		padding: 0.1rem 0.3rem;
		font-family: 'Sorts Mill Goudy Small Caps', serif;
		font-size: 0.9rem;
		letter-spacing: 0.05em;
		color: var(--map-ink);
		background: var(--map-paper);
		text-decoration: underline;
		white-space: nowrap;
	}

	.map {
		position: relative;
		block-size: min(70vh, 40rem);
	}

	.map[data-mini] {
		block-size: min(50vh, 20rem);
	}

	.canvas {
		position: absolute;
		inset: 0;
	}

	.overlay {
		position: absolute;
		inset-block-start: 0.5rem;
		inset-inline-start: 0.5rem;
		z-index: 2;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		align-items: start;
		max-block-size: calc(100% - 3rem);
		overflow: auto;
	}
</style>
