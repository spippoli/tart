<script lang="ts">
	import { recordHref } from '#lib/archive/records.ts';
	import type { Geometry } from '#lib/map/drawing.ts';
	import { m } from '#lib/paraglide/messages.js';
	import * as api from '../api';
	import type { RecordEditorState } from './state.svelte';

	/**
	 * The text readout of the Polygon step (Contribution and moderation spec, Other
	 * editors), announced to assistive technology: the vertex count, the number of Locations
	 * that fall within the polygon, and the existing Areas it overlaps. Overlaps are allowed.
	 */
	let { editor, geometry }: { editor: RecordEditorState; geometry: Geometry | null } = $props();
	const vertices = $derived(geometry?.type === 'Polygon' ? geometry.coordinates[0].length - 1 : 0);
	let readout = $state<api.AreaReadout | null>(null);
	let token = 0;

	$effect(() => {
		const shape = geometry;
		if (!shape || shape.type !== 'Polygon') {
			readout = null;
			return;
		}
		const mine = ++token;
		void api.areaReadout(shape).then((out) => {
			if (mine === token) readout = out.ok ? out.value : null;
		});
	});

	const words = $derived.by(() => {
		if (!geometry) return m.editor_area_readout_empty();
		const base = m.editor_area_readout({ vertices, locations: readout?.locations ?? 0 });
		const overlapping = readout?.overlapping ?? [];
		return overlapping.length === 0
			? `${base} ${m.editor_area_readout_no_overlap()}`
			: `${base} ${m.editor_area_readout_overlaps({ count: overlapping.length })}`;
	});
</script>

<div class="readout">
	<p role="status" aria-live="polite">{words}</p>
	{#if readout && readout.overlapping.length > 0}
		<ul aria-label={m.editor_area_overlaps_list()}>
			{#each readout.overlapping as area (area.id)}
				<li>
					<a
						href={recordHref('area', area.path, editor.config.locale)}
						target="_blank"
						rel="noopener"
					>
						{area.name}
						<span class="visually-hidden">{m.editor_new_tab()}</span>
					</a>
				</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.readout {
		display: grid;
		gap: 0.5rem;
	}

	p {
		margin: 0;
	}

	ul {
		margin: 0;
		padding-inline-start: 1.25rem;
	}
</style>
