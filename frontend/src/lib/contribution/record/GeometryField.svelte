<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import type { Bounds } from '#lib/map/bounds.ts';
	import { insideBounds, parseInInstance, type Point } from '#lib/map/coordinates.ts';
	import {
		addVertex,
		finish,
		fromGeometry,
		geometry,
		startDrawing,
		type Drawing,
		type Geometry,
		type Shape
	} from '#lib/map/drawing.ts';
	import DrawingTool from '#lib/map/DrawingTool.svelte';
	import type { View } from '#lib/map/engine.ts';
	import { describePoint } from '#lib/map/location-entry.ts';
	import { supportsWebGL2 } from '#lib/map/webgl.ts';
	import { m } from '#lib/paraglide/messages.js';

	/**
	 * A geometry to draw or correct (Contribution and moderation spec, Location step and
	 * Other editors): the drawing tool of the map module, by clicks or at a crosshair, and a
	 * coordinates field that is always there for a point or a line. When it corrects a
	 * geometry, the current one is drawn as a grey solid outline and the proposal over it
	 * dashed, and the legend says so in words. A polygon needs the map: without it the field
	 * says so. `value` is the geometry once the drawing can be finished, else `null`.
	 */
	let {
		id,
		value = $bindable(),
		reference = null,
		polygonOnly = false,
		boundary,
		view,
		attribution,
		locale,
		problem = null
	}: {
		id: string;
		value: Geometry | null;
		/** The geometry being corrected. */
		reference?: Geometry | null;
		/** A polygon is all that may be drawn (an Area). */
		polygonOnly?: boolean;
		boundary: Bounds;
		view: View;
		attribution: readonly { text: string; url: string }[];
		locale: string;
		/** Why the drawing cannot be used, in words, once a submit was tried. */
		problem?: string | null;
	} = $props();

	const shapeOf = (geometry: Geometry): Shape =>
		geometry.type === 'Point' ? 'point' : geometry.type === 'LineString' ? 'line' : 'polygon';

	// The tool opens on what the field holds, once; later changes of `value` are its own echoes.
	const first = untrack(() => value);
	let shape = $state<Shape>(
		untrack(() => polygonOnly) ? 'polygon' : first ? shapeOf(first) : 'point'
	);
	let drawing = $state<Drawing>(first ? fromGeometry(first) : startDrawing(untrack(() => shape)));
	$effect(() => {
		if (drawing.shape !== shape) drawing = startDrawing(shape);
	});

	let mapAvailable = $state(false);
	let mounted = $state(false);
	onMount(() => {
		mapAvailable = supportsWebGL2();
		mounted = true;
	});

	// The geometry is the drawing as soon as it can be finished: no separate *Done* is needed.
	const proposal = $derived(geometry(finish(drawing)));
	$effect(() => {
		const next = proposal;
		if (JSON.stringify(next) !== JSON.stringify(untrack(() => value))) value = next;
	});

	/** Where the map opens: on the geometry being corrected, else the Instance's view. */
	function centre(shape: Geometry | null): Point | null {
		if (!shape) return null;
		const positions =
			shape.type === 'Point'
				? [shape.coordinates]
				: shape.type === 'LineString'
					? shape.coordinates
					: shape.coordinates[0];
		const sum = positions.reduce<Point>(
			(all, each) => [all[0] + each[0], all[1] + each[1]],
			[0, 0]
		);
		return [sum[0] / positions.length, sum[1] / positions.length];
	}
	const opening = untrack(() => centre(reference ?? first));
	const startView: View = untrack(() => (opening ? { center: opening, zoom: 18 } : view));

	let text = $state('');
	let coordinatesError = $state<string | null>(null);
	let confirmed = $state<Point | null>(null);
	const coordinatesErrors: Record<string, () => string> = {
		empty: m.location_entry_error_empty,
		unrecognised: m.location_entry_error_unrecognised,
		short_link: m.location_entry_error_short_link,
		out_of_range: m.location_entry_error_out_of_range,
		outside_boundary: m.location_entry_error_outside_boundary
	};

	function useCoordinates() {
		const parsed = parseInInstance(text, boundary);
		if ('error' in parsed) {
			confirmed = null;
			coordinatesError = coordinatesErrors[parsed.error]();
			return;
		}
		coordinatesError = null;
		confirmed = parsed.point;
		if (!insideBounds(parsed.point, boundary)) return;
		const next = addVertex(drawing, parsed.point, boundary);
		drawing = shape === 'point' ? finish(next) : next;
	}

	const confirmation = $derived.by(() => {
		if (!confirmed) return null;
		const { latitude, longitude } = describePoint(confirmed, locale);
		return m.location_entry_confirm({ latitude, longitude });
	});

	const shapeWords = $derived(
		shape === 'point'
			? m.draw_shape_point()
			: shape === 'line'
				? m.draw_shape_line()
				: m.draw_shape_polygon()
	);
	const readout = $derived(
		m.editor_geometry_readout({ shape: shapeWords, count: drawing.vertices.length })
	);
</script>

<div class="geometry" {id} tabindex="-1">
	{#if !polygonOnly && mapAvailable}
		<fieldset class="shape">
			<legend>{m.draw_shape_legend()}</legend>
			{#each ['point', 'line', 'polygon'] as const as option (option)}
				<label>
					<input type="radio" name="{id}-shape" value={option} bind:group={shape} />
					{option === 'point'
						? m.draw_shape_point()
						: option === 'line'
							? m.draw_shape_line()
							: m.draw_shape_polygon()}
				</label>
			{/each}
		</fieldset>
	{/if}

	{#if !polygonOnly}
		<div class="coordinates">
			<label for="{id}-coordinates">{m.location_entry_coordinates_label()}</label>
			<p id="{id}-coordinates-hint" class="hint">{m.location_entry_coordinates_hint()}</p>
			<div class="row">
				<input
					id="{id}-coordinates"
					type="text"
					autocomplete="off"
					spellcheck="false"
					bind:value={text}
					aria-describedby="{id}-coordinates-hint {id}-coordinates-message"
					aria-invalid={coordinatesError ? 'true' : undefined}
					onkeydown={(event) => {
						if (event.key === 'Enter') {
							event.preventDefault();
							useCoordinates();
						}
					}}
				/>
				<button type="button" onclick={useCoordinates}>{m.location_entry_coordinates_use()}</button>
			</div>
			<p id="{id}-coordinates-message" class="message" role="status">
				{coordinatesError ?? confirmation ?? ''}
			</p>
		</div>
	{/if}

	{#if mapAvailable}
		{#if reference}
			<p class="legend">{m.editor_geometry_legend()}</p>
		{/if}
		<DrawingTool
			{drawing}
			ondrawing={(next) => (drawing = next)}
			view={startView}
			{boundary}
			inside={boundary}
			{attribution}
			{reference}
			onunavailable={() => (mapAvailable = false)}
		/>
	{:else if mounted && polygonOnly}
		<p class="notice">{m.editor_polygon_needs_map()}</p>
	{:else if mounted}
		<p class="notice">{m.location_entry_no_map()}</p>
	{/if}

	<p class="readout" role="status">{readout}</p>
	{#if problem}<p class="problem"><strong>{m.editor_error_prefix()}</strong> {problem}</p>{/if}
</div>

<style>
	.geometry {
		display: grid;
		gap: 1rem;
	}

	.shape {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem 1.5rem;
		border: 0;
		margin: 0;
		padding: 0;
	}

	.coordinates {
		display: grid;
		gap: 0.35rem;
	}

	.coordinates label {
		font-weight: 600;
	}

	.hint,
	.message,
	.notice,
	.legend,
	.readout,
	.problem {
		margin: 0;
	}

	.hint,
	.legend {
		color: var(--text-muted);
	}

	.message:empty {
		display: none;
	}

	.problem {
		border-inline-start: 4px solid var(--accent, currentColor);
		padding-inline-start: 0.5rem;
	}

	.row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.row input {
		flex: 1 1 14rem;
	}

	input[type='text'] {
		min-block-size: 2.75rem;
		padding-inline: 0.5rem;
		background: var(--background);
		color: var(--text);
		border: 1px solid var(--border);
	}

	button {
		min-block-size: 2.75rem;
		padding-inline: 0.75rem;
		background: var(--background);
		color: var(--text);
		border: 1px solid var(--border);
		cursor: pointer;
	}
</style>
