<script lang="ts">
	import { page } from '$app/state';
	import { m } from '#lib/paraglide/messages.js';
	import PageTitle from '../shell/PageTitle.svelte';
	import RecordAnchor from './RecordAnchor.svelte';
	import type { IndexPage } from './records';

	/**
	 * An index of Artists, Sites, Areas, or Series (archive-records spec, Indexes): by
	 * name, alphabetically in the Content language, 24 to a page; never by popularity.
	 * The "Filter by name" field belongs to Discovery.
	 */
	let { index, title }: { index: IndexPage; title: string } = $props();
	const pages = $derived(Math.max(1, Math.ceil(index.total / index.page_size)));
	const href = (number: number) => `${page.url.pathname}?page=${number}`;
</script>

<PageTitle {title} />

<h1>{title}</h1>
{#if index.items.length === 0}
	<p>{m.archive_index_empty()}</p>
{:else}
	<ul class="index">
		{#each index.items as item (item.id)}
			<li><RecordAnchor link={item} /></li>
		{/each}
	</ul>
{/if}
{#if pages > 1}
	<nav aria-label={m.archive_pagination()}>
		{#if index.page > 1}<a href={href(index.page - 1)} rel="prev">{m.archive_page_previous()}</a
			>{/if}
		<span>{m.archive_page_of({ page: String(index.page), pages: String(pages) })}</span>
		{#if index.page < pages}<a href={href(index.page + 1)} rel="next">{m.archive_page_next()}</a
			>{/if}
	</nav>
{/if}

<style>
	.index {
		columns: 16rem;
		padding-inline-start: 1.25rem;
	}
	nav {
		display: flex;
		gap: 1.5rem;
	}
</style>
