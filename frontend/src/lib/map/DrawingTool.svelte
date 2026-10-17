<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import type { Bounds } from './bounds';
	import type { Point } from './coordinates';
	import {
		addVertex,
		deleteSelected,
		finish,
		insertVertex,
		moveSelected,
		selectVertex,
		stepSelection,
		undo,
		type Drawing,
		type Event
	} from './drawing';
	import type { Camera, ClickEvent, ReferenceShape, View } from './engine';
	import Map from './Map.svelte';
	import type { Unavailable } from './style';

	/**
	 * The drawing mode of the map module (Discovery spec, Modules; Contribution and
	 * moderation, Location step). The drawing is the parent's: this component turns
	 * clicks and the crosshair buttons into the operations of `./drawing` and hands
	 * back the new `Drawing`. By clicks, or at a fixed crosshair at the map centre
	 * with buttons for every operation, so that the keyboard can do all that the
	 * pointer can (WCAG 2.1.1). What happened is announced in a live region.
	 */
	let {
		drawing,
		ondrawing,
		view,
		boundary,
		inside,
		attribution,
		onunavailable,
		reference = null
	}: {
		drawing: Drawing;
		ondrawing: (drawing: Drawing) => void;
		view: View;
		/** The bounding box of the Instance boundary. */
		boundary: Bounds;
		/** Where a vertex may be placed. */
		inside: Bounds;
		attribution: readonly { text: string; url: string }[];
		onunavailable: (reason: Unavailable) => void;
		/** The current geometry of a record being corrected, drawn grey under the drawing. */
		reference?: ReferenceShape | null;
	} = $props();

	let mode = $state<'click' | 'crosshair'>('click');
	let moved = $state<Point>();
	const centre = $derived<Point>(moved ?? [view.center[0], view.center[1]]);
	let map = $state<ReturnType<typeof Map>>();
	const id = $props.id();

	const { vertices, selected } = $derived(drawing);
	const drawn = $derived({
		vertices,
		ring: drawing.shape === 'polygon',
		selected,
		midpoints: drawing.shape !== 'point',
		reference
	});
	const canEdit = $derived(drawing.shape !== 'point');
	const hasSelection = $derived(selected !== null);

	function click({ point, handle }: ClickEvent) {
		if (mode !== 'click') return;
		if (handle?.kind === 'vertex') {
			ondrawing(selectVertex(drawing, handle.index === selected ? null : handle.index));
		} else if (handle?.kind === 'midpoint') {
			const from = vertices[handle.index];
			const to = vertices[(handle.index + 1) % vertices.length];
			const middle: Point = [(from[0] + to[0]) / 2, (from[1] + to[1]) / 2];
			ondrawing(insertVertex(drawing, handle.index, middle, inside));
		} else if (selected !== null) {
			ondrawing(moveSelected(drawing, point, inside));
		} else {
			ondrawing(addVertex(drawing, point, inside));
		}
	}

	function selectStep(step: 1 | -1) {
		const next = stepSelection(drawing, step);
		ondrawing(next);
		if (next.selected !== null) map?.centerOn(next.vertices[next.selected]);
	}

	function problemText(event: Extract<Event, { type: 'rejected' }>): string {
		switch (event.problem) {
			case 'outside_boundary':
				return m.draw_problem_outside_boundary();
			case 'self_intersecting':
				return m.draw_problem_self_intersecting();
			case 'nothing_to_do':
				return m.draw_problem_nothing_to_do();
			case 'too_few_vertices':
				return drawing.shape === 'point'
					? m.draw_problem_too_few_point()
					: drawing.shape === 'line'
						? m.draw_problem_too_few_line()
						: m.draw_problem_too_few_polygon();
		}
	}

	/** What the last operation did, in words, for the live region. */
	const announcement = $derived.by(() => {
		const event = drawing.last;
		const number = 'index' in event ? event.index + 1 : 0;
		switch (event.type) {
			case 'started':
				return m.draw_event_started();
			case 'added':
				return m.draw_event_added({ number });
			case 'moved':
				return m.draw_event_moved({ number });
			case 'inserted':
				return m.draw_event_inserted({ number });
			case 'deleted':
				return m.draw_event_deleted({ number });
			case 'selected':
				return m.draw_event_selected({ number });
			case 'deselected':
				return m.draw_event_deselected();
			case 'undone':
				return m.draw_event_undone();
			case 'finished':
				return m.draw_event_finished();
			case 'rejected':
				return problemText(event);
		}
	});

	function track(camera: Camera) {
		moved = [camera.center[0], camera.center[1]];
	}
</script>

<div class="tool">
	<fieldset class="modes">
		<legend>{m.draw_mode_legend()}</legend>
		<label>
			<input type="radio" name="{id}-mode" value="click" bind:group={mode} />
			{m.draw_mode_click()}
		</label>
		<label>
			<input type="radio" name="{id}-mode" value="crosshair" bind:group={mode} />
			{m.draw_mode_crosshair()}
		</label>
	</fieldset>

	<p class="hint">{mode === 'click' ? m.draw_click_hint() : m.draw_crosshair_hint()}</p>

	<div class="stage">
		<Map
			bind:this={map}
			{view}
			{boundary}
			{attribution}
			{onunavailable}
			onmoveend={track}
			onclick={click}
			{drawn}
		/>
		{#if mode === 'crosshair'}
			<div class="crosshair" role="img" aria-label={m.draw_crosshair_mark()}></div>
		{/if}
	</div>

	<div class="buttons">
		{#if mode === 'crosshair'}
			<button type="button" onclick={() => ondrawing(addVertex(drawing, centre, inside))}>
				{m.draw_add_here()}
			</button>
			{#if canEdit}
				<button type="button" onclick={() => selectStep(-1)} disabled={vertices.length === 0}>
					{m.draw_select_previous()}
				</button>
				<button type="button" onclick={() => selectStep(1)} disabled={vertices.length === 0}>
					{m.draw_select_next()}
				</button>
			{/if}
			<button
				type="button"
				onclick={() => ondrawing(moveSelected(drawing, centre, inside))}
				disabled={!hasSelection}
			>
				{m.draw_move_here()}
			</button>
			{#if canEdit}
				<button
					type="button"
					onclick={() => ondrawing(insertVertex(drawing, selected!, centre, inside))}
					disabled={!hasSelection}
				>
					{m.draw_insert_here()}
				</button>
			{/if}
		{/if}
		{#if canEdit && (mode === 'crosshair' || hasSelection)}
			<button
				type="button"
				onclick={() => ondrawing(deleteSelected(drawing))}
				disabled={!hasSelection}
			>
				{m.draw_delete()}
			</button>
		{/if}
		<button
			type="button"
			onclick={() => ondrawing(undo(drawing))}
			disabled={drawing.history.length === 0}
		>
			{m.draw_undo()}
		</button>
		<button type="button" onclick={() => ondrawing(finish(drawing))}>{m.draw_done()}</button>
	</div>

	<p class="count">{m.draw_status_count({ count: vertices.length })}</p>
	<p class="status" role="status">{announcement}</p>
</div>

<style>
	.tool {
		display: grid;
		gap: 0.75rem;
	}

	.modes {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem 1.5rem;
		border: 0;
		margin: 0;
		padding: 0;
	}

	.hint,
	.count,
	.status {
		margin: 0;
	}

	.stage {
		position: relative;
	}

	/* A fixed crosshair at the centre of the map; the ring and the cross are drawn
	   in the text colour with a paper halo, so that it reads on any basemap. */
	.crosshair {
		position: absolute;
		inset-block-start: 50%;
		inset-inline-start: 50%;
		inline-size: 2.5rem;
		block-size: 2.5rem;
		translate: -50% -50%;
		border: 2px solid var(--text);
		border-radius: 50%;
		box-shadow: 0 0 0 2px var(--background);
		pointer-events: none;
		z-index: 1;
		background:
			linear-gradient(var(--text), var(--text)) center / 2px 100% no-repeat,
			linear-gradient(var(--text), var(--text)) center / 100% 2px no-repeat;
	}

	.buttons {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	button {
		min-block-size: 2.75rem;
		padding-inline: 0.75rem;
		background: var(--background);
		color: var(--text);
		border: 1px solid var(--border);
		cursor: pointer;
	}

	button:disabled {
		cursor: default;
		opacity: 0.6;
	}
</style>
