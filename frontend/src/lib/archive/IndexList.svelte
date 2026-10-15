<script lang="ts">
	import { page } from '$app/state';
	import { m } from '#lib/paraglide/messages.js';
	import PageTitle from '../shell/PageTitle.svelte';
	import { indexQueryString, readIndexQuery } from './index-query';
	import RecordAnchor from './RecordAnchor.svelte';
	import type { IndexPage } from './records';

	/**
	 * An index of Artists, Sites, Areas, or Series (archive-records spec, Indexes): by
	 * name, alphabetically in the Content language, 24 to a page; never by popularity.
	 * The "Filter by name" field (Discovery spec, Index name filter) is a plain form
	 * that works without JavaScript: it reloads the index with `?nome=` (`?name=`).
	 */
	let { index, title }: { index: IndexPage; title: string } = $props();
	const pages = $derived(Math.max(1, Math.ceil(index.total / index.page_size)));
	const name = $derived(readIndexQuery(page.url.searchParams).name);
	const href = (number: number) =>
		`${page.url.pathname}${indexQueryString({ page: number, name })}`;
</script>

<PageTitle {title} />

<h1>{title}</h1>

<form method="get" role="search" aria-label={m.archive_index_filter_label()}>
	<label for="index-filter">{m.archive_index_filter_label()}</label>
	<input id="index-filter" type="search" name={m.query_key_name()} value={name ?? ''} />
	<button type="submit">{m.archive_index_filter_apply()}</button>
	{#if name}<a href={page.url.pathname}>{m.archive_index_filter_clear()}</a>{/if}
</form>

{#if index.items.length === 0}
	<p>{name ? m.archive_index_no_match({ name }) : m.archive_index_empty()}</p>
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
	form {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem 0.75rem;
		align-items: center;
		margin-block-end: 1rem;
	}
	.index {
		columns: 16rem;
		padding-inline-start: 1.25rem;
	}
	nav {
		display: flex;
		gap: 1.5rem;
	}
</style>
