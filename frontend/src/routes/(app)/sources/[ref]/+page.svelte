<script lang="ts">
	import Content from '#lib/archive/Content.svelte';
	import { archiveContext } from '#lib/archive/context.svelte.ts';
	import LinkList from '#lib/archive/LinkList.svelte';
	import ModeratorNotice from '#lib/archive/ModeratorNotice.svelte';
	import RecordFooter from '#lib/archive/RecordFooter.svelte';
	import { archiveDate } from '#lib/archive/records.ts';
	import { languageName } from '#lib/i18n/format.ts';
	import { m } from '#lib/paraglide/messages.js';
	import PageTitle from '#lib/shell/PageTitle.svelte';
	import type { PageProps } from './$types';

	/**
	 * The Source page (archive-records spec, criterion 45): the rendered citation
	 * "Author, *Title*, Publication, Date", omitting absent parts, then the URL; its Note;
	 * and what cites it.
	 */
	let { data }: PageProps = $props();
	const source = $derived(data.source);
	const context = archiveContext();
	const title = $derived(source.title ?? m.archive_content_redacted());
	const language = $derived(source.language ?? context.contentLanguage);
	const separator = ', ';
	// "Author, *Title*, Publication, Date", omitting absent parts (criterion 45).
	const parts = $derived(
		[
			source.author ? { text: source.author, content: true, cite: false } : null,
			{ text: source.title, content: true, cite: true },
			source.publication ? { text: source.publication, content: true, cite: false } : null,
			source.date
				? { text: archiveDate(source.date, context.dates), content: false, cite: false }
				: null
		].filter((part) => part !== null)
	);
</script>

<PageTitle {title} />

<article>
	<ModeratorNotice withdrawnAt={source.withdrawn_at} />
	<p class="kind">{m.archive_kind_source()}</p>
	<h1><Content text={source.title} {language} redacted={!source.title} /></h1>
	<p class="citation">
		{#each parts as part, index (index)}{#if index > 0}{separator}{/if}{#if part.cite}<cite
					><Content text={part.text} {language} redacted={!part.text} /></cite
				>{:else if part.content}<Content
					text={part.text}
					{language}
				/>{:else}{part.text}{/if}{/each}
	</p>
	{#if source.url}<p><a href={source.url} rel="external noopener">{source.url}</a></p>{/if}
	{#if source.language}
		<p>{m.archive_source_language({ language: languageName(source.language, context) })}</p>
	{/if}
	{#if source.note}
		<section aria-labelledby="note">
			<h2 id="note">{m.archive_note()}</h2>
			<Content text={source.note} block />
		</section>
	{/if}
	<section aria-labelledby="cited-by">
		<h2 id="cited-by">{m.archive_source_cited_by()}</h2>
		{#if source.cited_by.length > 0}
			<p><LinkList links={source.cited_by} /></p>
		{:else}
			<p>{m.archive_none()}</p>
		{/if}
	</section>
	<RecordFooter kind="source" id={source.id} path={source.path} />
</article>

<style>
	.kind {
		color: var(--text-muted);
		margin-block-end: 0;
	}
</style>
