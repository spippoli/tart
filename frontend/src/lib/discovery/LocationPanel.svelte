<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import Content from '#lib/archive/Content.svelte';
	import { archiveContext } from '#lib/archive/context.svelte.ts';
	import LinkList from '#lib/archive/LinkList.svelte';
	import RecordAnchor from '#lib/archive/RecordAnchor.svelte';
	import { locationTitleText, recordHref } from '#lib/archive/records.ts';
	import type { components } from '../api/schema';
	import ListEntry from './ListEntry.svelte';

	type Panel = components['schemas']['LocationPanel'];

	/**
	 * The side panel on a wide screen and the bottom sheet on a narrow one (Discovery
	 * spec, Selection and the side panel): the Location header, the stratigraphy of the
	 * Artworks that match the filters, a line for those that do not, and a link to the
	 * Location page. It is never a popup anchored to a sign. The page moves focus to its
	 * title and Esc or "Close" closes it.
	 */
	let {
		status,
		panel,
		onclose,
		onclear,
		onretry,
		title = $bindable()
	}: {
		status: 'loading' | 'ready' | 'failed';
		panel: Panel | null;
		onclose: () => void;
		/** "Clear filters", in the case of a Location no Artwork of which matches. */
		onclear: () => void;
		onretry: () => void;
		title?: HTMLElement;
	} = $props();
	const context = archiveContext();

	const location = $derived(panel?.location);
	const heading = $derived(
		location
			? locationTitleText(location.id, location.title, context.surfaceType, context.locale)
			: m.discovery_panel_loading()
	);
</script>

<section class="panel" aria-labelledby="panel-title">
	<div class="head">
		<h2 id="panel-title" tabindex="-1" bind:this={title}>
			{#if location?.title.place_description}<Content
					text={location.title.place_description}
				/>{:else}{heading}{/if}
		</h2>
		<button type="button" onclick={onclose}>{m.discovery_panel_close()}</button>
	</div>

	{#if status === 'failed'}
		<p>{m.discovery_panel_failed()}</p>
		<p><button type="button" onclick={onretry}>{m.discovery_retry()}</button></p>
	{:else if status === 'ready' && panel && location}
		<dl>
			<dt class="visually-hidden">{m.archive_surface_type()}</dt>
			<dd>{m.discovery_panel_surface({ type: context.surfaceType(location.surface_type) })}</dd>
			{#if location.approximate}
				<dd>
					{location.uncertainty_radius
						? m.discovery_panel_approximate_radius({ radius: location.uncertainty_radius })
						: m.discovery_panel_approximate_no_radius()}
				</dd>
			{/if}
			{#if panel.site}
				<dt>{m.archive_site()}</dt>
				<dd><RecordAnchor link={panel.site} /></dd>
			{/if}
			{#if panel.areas.length > 0}
				<dt>{m.archive_areas()}</dt>
				<dd><LinkList links={panel.areas} /></dd>
			{/if}
		</dl>
		<p><a href={recordHref('location', location.path)}>{m.discovery_panel_open_location()}</a></p>

		{#if panel.entries.length === 0}
			<p class="note">{m.archive_no_public_artworks_here()}</p>
		{:else}
			{#if !panel.matches}
				<p class="note">{m.discovery_panel_no_match()}</p>
				<p><button type="button" onclick={onclear}>{m.discovery_panel_clear()}</button></p>
			{/if}
			<ul class="strata" aria-label={m.discovery_panel_artworks()}>
				{#each panel.entries as entry (entry.id)}
					<li><ListEntry {entry} where={false} /></li>
				{/each}
			</ul>
			{#if panel.other > 0}
				<p class="note">
					{panel.other === 1
						? m.discovery_panel_other_one()
						: m.discovery_panel_other_other({ count: panel.other })}
				</p>
			{/if}
		{/if}
	{/if}
</section>

<style>
	.panel {
		box-sizing: border-box;
		display: grid;
		gap: 0.5rem;
		align-content: start;
		padding: 0.75rem;
		min-block-size: 0;
		overflow: auto;
		background: var(--background);
		border: 2px solid var(--text);
	}
	.head {
		display: flex;
		gap: 0.5rem;
		justify-content: space-between;
		align-items: start;
	}
	h2 {
		margin: 0;
		font-size: 1.125rem;
	}
	h2:focus-visible {
		outline: 3px solid var(--text);
		outline-offset: 2px;
	}
	dl,
	p {
		margin: 0;
	}
	dd {
		margin: 0;
	}
	dt:not(.visually-hidden) {
		font-weight: 700;
	}
	.strata {
		display: grid;
		gap: 0.5rem;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.note {
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--border);
		background: var(--surface);
	}
</style>
