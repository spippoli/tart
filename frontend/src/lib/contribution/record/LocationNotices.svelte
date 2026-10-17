<script lang="ts">
	import { locationTitleText, vocabularyLabels } from '#lib/archive/records.ts';
	import type { Geometry } from '#lib/map/drawing.ts';
	import { parseRadius } from '#lib/map/location-entry.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { localizeHref } from '#lib/paraglide/runtime.js';
	import * as api from '../api';
	import type { RecordEditorState } from './state.svelte';

	/**
	 * The two notices of a Location edit (Contribution and moderation spec, Other editors).
	 * Always: how many Artworks the Location carries, since the change applies to all of
	 * them. When the proposed geometry falls within the proximity rule of another Location:
	 * if it is the same surface, propose a Merge, linking the Merge editor with both records
	 * filled in. A geometry edit is a correction and creates no History event.
	 */
	let { editor }: { editor: RecordEditorState } = $props();
	const config = $derived(editor.config);
	const count = $derived(config.artworkCount ?? 0);
	const proposed = $derived(editor.form.fields.geometry as Geometry | null | undefined);
	const radius = $derived.by(() => {
		const entered = editor.form.fields.uncertainty_radius;
		if (typeof entered === 'string') {
			const parsed = parseRadius(entered);
			return 'metres' in parsed ? parsed.metres : null;
		}
		const stored = config.current.uncertainty_radius;
		return typeof stored === 'number' ? stored : null;
	});
	const surfaceLabel = $derived(vocabularyLabels(config.surfaceTypes, config.locale));
	let near = $state<{ id: number; title: string }[]>([]);
	let token = 0;

	$effect(() => {
		const geometry = proposed;
		const metres = radius;
		if (!geometry) {
			near = [];
			return;
		}
		const mine = ++token;
		void api.locationCandidates({ geometry, radius: metres }).then((out) => {
			if (mine !== token) return;
			near = out.ok
				? out.value.candidates
						.filter((each) => each.location.id !== config.targetId)
						.map((each) => ({
							id: each.location.id,
							title: locationTitleText(
								each.location.id,
								each.location.title,
								surfaceLabel,
								config.locale
							)
						}))
				: [];
			if (near.length > 0)
				editor.announce(m.editor_location_merge_announcement({ count: near.length }));
		});
	});

	function mergeHref(into: number): string {
		const query = new URLSearchParams({
			kind: 'location',
			from: String(config.targetId),
			into: String(into)
		});
		return `${localizeHref('/contribute/merge')}?${query}`;
	}
</script>

<aside class="notices" aria-label={m.editor_location_notices()}>
	<p class="notice" data-location-artworks>
		{new Intl.PluralRules(config.locale).select(count) === 'one'
			? m.editor_location_artworks_one({ count })
			: m.editor_location_artworks_other({
					count: new Intl.NumberFormat(config.locale).format(count)
				})}
	</p>
	{#if near.length > 0}
		<div class="notice" data-location-merge>
			<p>{m.editor_location_merge()}</p>
			<ul>
				{#each near as each (each.id)}
					<li>
						<a href={mergeHref(each.id)}>{m.editor_location_merge_link({ title: each.title })}</a>
					</li>
				{/each}
			</ul>
		</div>
	{/if}
</aside>

<style>
	.notices {
		display: grid;
		gap: 0.75rem;
	}

	.notice {
		border-inline-start: 4px solid var(--border);
		padding-inline-start: 0.75rem;
		margin: 0;
	}

	.notice p {
		margin: 0 0 0.35rem;
	}

	ul {
		margin: 0;
		padding-inline-start: 1.25rem;
	}
</style>
