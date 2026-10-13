<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import { licence } from '#lib/licences.ts';
	import Content from './Content.svelte';
	import { archiveContext } from './context.svelte';
	import { archiveDate, mediumWord, recordHref, type DocumentationSummary } from './records';

	/**
	 * Documentation items: each with its Observed date as text, its Creator credit, and
	 * its licence, which covers the file only (criteria 23, 32, 36). An image shows its
	 * `view` rendition with its alt text; a PDF its preview with the platform's alt text.
	 * Every item links to its own page; nothing depends on hover.
	 */
	let { items }: { items: DocumentationSummary[] } = $props();
	const context = archiveContext();
</script>

{#if items.length === 0}
	<p class="empty">{m.archive_gallery_empty()}</p>
{:else}
	<ul class="gallery">
		{#each items as item (item.id)}
			<li>
				<figure>
					{#if item.file && (item.medium === 'image' || item.medium === 'pdf')}
						{@const size = item.renditions?.view}
						<img
							src="/api/media/{item.file}/view"
							alt={item.medium === 'image' ? item.alt_text : m.archive_pdf_preview_alt()}
							lang={item.medium === 'image' ? context.contentLanguage : undefined}
							width={size?.width}
							height={size?.height}
							loading="lazy"
						/>
					{:else if item.medium === 'text'}
						<blockquote><Content text={item.text} language={item.language} block /></blockquote>
					{:else if item.url}
						<p><a href={item.url} rel="external noopener">{m.archive_open_link()}</a></p>
					{/if}
					<figcaption>
						<span class="date">{archiveDate(item.observed_date, context.dates)}</span>
						· {mediumWord(item.medium, context.locale)}
						{#if item.creator_credit}
							<br />{m.archive_credit({ credit: item.creator_credit })}
						{/if}
						{#if item.licence}
							{@const shown = licence(item.licence, context.locale)}
							<br /><a href={shown.url} rel="license external"
								>{m.archive_licence_file_only({
									licence: shown.label
								})}</a
							>
						{/if}
						<br /><a href={recordHref('documentation_item', item.path)}
							>{m.archive_document_link()}</a
						>
					</figcaption>
				</figure>
			</li>
		{/each}
	</ul>
{/if}

<style>
	.gallery {
		list-style: none;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr));
		gap: 1rem;
	}
	figure {
		margin: 0;
	}
	img {
		max-width: 100%;
		height: auto;
		background: var(--surface);
	}
	figcaption,
	.empty {
		color: var(--text-muted);
		font-size: 0.95em;
	}
	blockquote {
		margin: 0;
		padding-inline-start: 1rem;
		border-inline-start: 3px solid var(--border);
	}
</style>
