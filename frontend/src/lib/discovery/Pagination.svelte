<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';

	/**
	 * Numbered pages (Discovery spec, List entries): previous and next links and the page
	 * numbers, as plain links; there is no infinite scroll and no cap. Around a long run
	 * of pages only the first, the last, and the neighbours of the current one are shown.
	 */
	let {
		current,
		pages,
		href,
		onpage
	}: {
		current: number;
		pages: number;
		href: (page: number) => string;
		/** Takes over a click: the Explore list pages in the page, with no page number in the URL. */
		onpage?: (page: number) => void;
	} = $props();

	/** The click of a page link, left to the browser for a new tab or window. */
	function go(event: MouseEvent, number: number) {
		if (!onpage || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey) return;
		event.preventDefault();
		onpage(number);
	}

	const numbers = $derived(
		[...new Set([1, current - 2, current - 1, current, current + 1, current + 2, pages])]
			.filter((number) => number >= 1 && number <= pages)
			.sort((a, b) => a - b)
	);
</script>

{#if pages > 1}
	<nav aria-label={m.archive_pagination()}>
		<ul>
			{#if current > 1}
				<li>
					<a href={href(current - 1)} rel="prev" onclick={(event) => go(event, current - 1)}
						>{m.archive_page_previous()}</a
					>
				</li>
			{/if}
			{#each numbers as number, index (number)}
				{#if index > 0 && number - numbers[index - 1] > 1}<li aria-hidden="true">…</li>{/if}
				<li>
					<a
						href={href(number)}
						onclick={(event) => go(event, number)}
						aria-label={m.discovery_page_number({ page: number })}
						aria-current={number === current ? 'page' : undefined}>{number}</a
					>
				</li>
			{/each}
			{#if current < pages}
				<li>
					<a href={href(current + 1)} rel="next" onclick={(event) => go(event, current + 1)}
						>{m.archive_page_next()}</a
					>
				</li>
			{/if}
		</ul>
	</nav>
{/if}

<style>
	ul {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem 1rem;
		margin: 1rem 0;
		padding: 0;
		list-style: none;
	}
	a {
		display: inline-block;
		min-inline-size: 1.5rem;
		padding: 0.25rem 0.25rem;
		text-align: center;
	}
	a[aria-current='page'] {
		font-weight: 700;
		text-decoration: none;
		border-block-end: 3px solid var(--accent);
	}
</style>
