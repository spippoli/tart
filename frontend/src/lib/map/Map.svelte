<script lang="ts">
	import { onMount } from 'svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { mapBounds, type Bounds } from './bounds';
	import type { Camera, ClickEvent, Drawn, Engine, View } from './engine';
	import type { Point } from './coordinates';
	import Legend from './Legend.svelte';
	import MapControl from './MapControl.svelte';
	import { DARK_SCHEME, fetchStyle, type Theme, type Tokens, type Unavailable } from './style';
	import { supportsWebGL2 } from './webgl';

	/**
	 * The map module (Discovery spec, Modules): renders a map from the served style
	 * of the UI theme into its container, with the map control, the legend, and the
	 * attribution, kept within the boundary plus 2 km and below z19. It reports
	 * `onunavailable` without WebGL2, when the style fails to load, or when the tile
	 * extract is missing, and then renders nothing. The camera after each move is
	 * on the root's `data-*` attributes and given to `onmoveend`.
	 */
	let {
		view,
		boundary,
		attribution,
		onunavailable,
		onmoveend,
		onclick,
		drawn = null
	}: {
		/** The Instance's default view, which the reset button returns to. */
		view: View;
		/** The bounding box of the Instance boundary. */
		boundary: Bounds;
		attribution: readonly { text: string; url: string }[];
		onunavailable: (reason: Unavailable) => void;
		onmoveend?: (camera: Camera) => void;
		/** Clicks on the map, for the drawing tool. */
		onclick?: (click: ClickEvent) => void;
		/** The shape being drawn, for the drawing tool. */
		drawn?: Drawn | null;
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
					bounds: mapBounds(boundary),
					attribution,
					labels: { canvas: m.map_canvas(), attributionToggle: m.map_attribution_toggle() },
					onClick: onclick && ((click) => onclick(click)),
					onMoveEnd(moved) {
						camera = moved;
						onmoveend?.(moved);
					}
				});
				if (gone) created.destroy();
				else engine = created;
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
</script>

{#if !unavailable}
	<div
		class="map"
		data-state={engine ? 'ready' : 'loading'}
		data-zoom={camera?.zoom}
		data-lon={camera?.center[0]}
		data-lat={camera?.center[1]}
		data-bearing={camera?.bearing}
		data-pitch={camera?.pitch}
	>
		<div class="overlay" role="group" aria-label={m.map_controls()}>
			{#if engine}
				<MapControl {engine} />
			{/if}
			{#if tokens}
				<Legend {tokens} />
			{/if}
		</div>
		<div class="canvas" bind:this={container}></div>
	</div>
{/if}

<style>
	.map {
		position: relative;
		block-size: min(70vh, 40rem);
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
