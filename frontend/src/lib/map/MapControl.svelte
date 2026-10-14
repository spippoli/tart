<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import type { Engine } from './engine';

	// Pan and zoom without dragging (WCAG 2.5.7, ADR 0017): zoom in and out, four pan
	// buttons that move a third of the view, and a return to the default view. Under
	// prefers-reduced-motion MapLibre makes every move instant.
	let { engine, zoomOnly = false }: { engine: Engine; zoomOnly?: boolean } = $props();

	// In reading order, so that focus follows the layout.
	const moves = [
		{ label: m.map_pan_north, glyph: '↑', area: 'north', move: () => engine.pan(0, -1) },
		{ label: m.map_pan_west, glyph: '←', area: 'west', move: () => engine.pan(-1, 0) },
		{ label: m.map_reset, glyph: '⌂', area: 'reset', move: () => engine.reset() },
		{ label: m.map_pan_east, glyph: '→', area: 'east', move: () => engine.pan(1, 0) },
		{ label: m.map_pan_south, glyph: '↓', area: 'south', move: () => engine.pan(0, 1) }
	];
</script>

<div class="control">
	<div class="zoom">
		<button type="button" onclick={() => engine.zoomIn()}>
			<span aria-hidden="true">+</span><span class="visually-hidden">{m.map_zoom_in()}</span>
		</button>
		<button type="button" onclick={() => engine.zoomOut()}>
			<span aria-hidden="true">−</span><span class="visually-hidden">{m.map_zoom_out()}</span>
		</button>
	</div>
	{#if !zoomOnly}
		<div class="pan">
			{#each moves as { label, glyph, area, move } (area)}
				<button type="button" style:grid-area={area} onclick={move}>
					<span aria-hidden="true">{glyph}</span><span class="visually-hidden">{label()}</span>
				</button>
			{/each}
		</div>
	{/if}
</div>

<style>
	.control {
		display: flex;
		gap: 0.5rem;
		align-items: start;
	}

	.zoom {
		display: grid;
		gap: 2px;
	}

	.pan {
		display: grid;
		grid-template-areas:
			'. north .'
			'west reset east'
			'. south .';
		gap: 2px;
	}

	button {
		inline-size: 2.75rem;
		block-size: 2.75rem;
		padding: 0;
		font-size: 1.25rem;
		line-height: 1;
		background: var(--background);
		color: var(--text);
		border: 1px solid var(--border);
		cursor: pointer;
	}

	button:hover {
		background: var(--surface);
	}
</style>
