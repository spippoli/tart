<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import { getLocale, localizeHref } from '#lib/paraglide/runtime.js';
	import RecordAnchor from '#lib/archive/RecordAnchor.svelte';
	import { ROUTES, type Kind } from '#lib/archive/records.ts';
	import type { components } from '../api/schema';
	import { queryKey } from './state';

	/**
	 * The "Also matching" box (Discovery spec, Search): at most three records per kind of
	 * Artists, Series, Sites, and Areas whose name or Alias matches the search, each kind
	 * ending in "Show all (N)" to its index filtered by name when there are more.
	 * Absent without a match; the API leaves it out.
	 */
	let {
		also,
		query
	}: { also: components['schemas']['AlsoMatching'] | null; query: string | null } = $props();
	const locale = getLocale();

	const headings: Partial<Record<Kind, () => string>> = {
		artist: m.archive_index_artists,
		series: m.archive_index_series,
		site: m.archive_index_sites,
		area: m.archive_index_areas
	};
	const allHref = (kind: Kind) =>
		`${localizeHref(ROUTES[kind])}?${new URLSearchParams({ [queryKey('name', locale)]: query ?? '' })}`;
</script>

{#if also && also.kinds.length > 0}
	<section class="also" aria-labelledby="also-matching">
		<h2 id="also-matching">{m.discovery_also_matching()}</h2>
		{#each also.kinds as group (group.kind)}
			<h3>{headings[group.kind]?.()}</h3>
			<ul>
				{#each group.items as item (item.record.id)}
					<li>
						<RecordAnchor link={item.record} />
						{#if item.alias}
							<span class="alias">{m.discovery_also_alias({ alias: item.alias })}</span>
						{/if}
					</li>
				{/each}
			</ul>
			{#if group.total > group.items.length}
				<p><a href={allHref(group.kind)}>{m.discovery_also_show_all({ count: group.total })}</a></p>
			{/if}
		{/each}
	</section>
{/if}

<style>
	.also {
		margin-block: 1rem;
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--border);
		border-radius: 4px;
	}
	h2,
	h3 {
		margin: 0.25rem 0;
		font-size: 1rem;
	}
	h3 {
		color: var(--text-muted);
	}
	ul {
		margin: 0;
		padding-inline-start: 1.25rem;
	}
	p {
		margin: 0.25rem 0;
	}
	.alias {
		color: var(--text-muted);
	}
</style>
