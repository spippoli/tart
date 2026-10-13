<script lang="ts">
	import ArtworkCards from '#lib/archive/ArtworkCards.svelte';
	import Content from '#lib/archive/Content.svelte';
	import { archiveContext } from '#lib/archive/context.svelte.ts';
	import ModeratorNotice from '#lib/archive/ModeratorNotice.svelte';
	import RecordFooter from '#lib/archive/RecordFooter.svelte';
	import { archiveDate, locationTitleText, mediumWord, recordHref } from '#lib/archive/records.ts';
	import { formatDate } from '#lib/i18n/format.ts';
	import { licence } from '#lib/licences.ts';
	import { m } from '#lib/paraglide/messages.js';
	import PageTitle from '#lib/shell/PageTitle.svelte';
	import type { PageProps } from './$types';

	/**
	 * The Documentation item page (archive-records spec, criteria 23, 28, 32): the file's
	 * rendition or preview with its alt text (or the text, or the link), its three dates,
	 * Creator credit, licence covering the file only, Rights basis in words, the origin of
	 * a third party's work, the Artworks it documents, and the Location of a disappearance.
	 */
	let { data }: PageProps = $props();
	const item = $derived(data.item);
	const context = archiveContext();
	const title = $derived(
		m.archive_document_title({
			medium: mediumWord(item.medium, context.locale),
			date: archiveDate(item.observed_date, context.dates)
		})
	);
	const shownLicence = $derived(item.licence ? licence(item.licence, context.locale) : null);
	const size = $derived(item.renditions?.large);
</script>

<PageTitle {title} />

<article>
	<ModeratorNotice withdrawnAt={item.withdrawn_at} />
	<h1>{title.charAt(0).toUpperCase() + title.slice(1)}</h1>

	{#if item.file && (item.medium === 'image' || item.medium === 'pdf')}
		<img
			src="/api/media/{item.file}/large"
			alt={item.medium === 'image' ? item.alt_text : m.archive_pdf_preview_alt()}
			lang={item.medium === 'image' ? context.contentLanguage : undefined}
			width={size?.width}
			height={size?.height}
		/>
	{:else if item.medium === 'text'}
		<h2>{m.archive_document_text()}</h2>
		<Content text={item.text} language={item.language} block />
	{:else if item.url}
		<p><a href={item.url} rel="external noopener">{m.archive_open_link()}</a></p>
	{/if}

	<dl>
		<dt>{m.archive_document_observed()}</dt>
		<dd>{archiveDate(item.observed_date, context.dates)}</dd>
		<dt>{m.archive_document_submitted()}</dt>
		<dd>{formatDate(item.submitted_at, context.dates)}</dd>
		<dt>{m.archive_document_approved()}</dt>
		<dd>{formatDate(item.approved_at, context.dates)}</dd>
		{#if item.creator_credit}
			<dt>{m.archive_document_creator()}</dt>
			<dd><Content text={item.creator_credit} /></dd>
		{/if}
		{#if shownLicence}
			<dt>{m.archive_document_licence()}</dt>
			<dd>
				<a href={shownLicence.url} rel="license external">{shownLicence.name}</a>
				({m.archive_document_licence_scope()})
			</dd>
		{/if}
		{#if item.rights_basis}
			<dt>{m.archive_document_rights()}</dt>
			<dd>
				{item.rights_basis === 'own_work'
					? m.archive_rights_own_work()
					: m.archive_rights_third_party()}
			</dd>
		{/if}
		{#if item.origin_url}
			<dt>{m.archive_document_origin()}</dt>
			<dd><a href={item.origin_url} rel="external noopener">{item.origin_url}</a></dd>
		{/if}
		{#if item.location}
			<dt>{m.archive_document_disappearance()}</dt>
			<dd>
				<a href={recordHref('location', item.location.path)}
					>{locationTitleText(
						item.location.id,
						item.location.title,
						context.surfaceType,
						context.locale
					)}</a
				>
			</dd>
		{/if}
	</dl>

	<section aria-labelledby="documents">
		<h2 id="documents">{m.archive_document_artworks()}</h2>
		<ArtworkCards cards={item.artworks} />
	</section>

	<RecordFooter kind="documentation_item" id={item.id} path={item.path} />
</article>

<style>
	img {
		max-width: 100%;
		height: auto;
		background: var(--surface);
	}
	dl {
		display: grid;
		grid-template-columns: max-content 1fr;
		gap: 0.25rem 1rem;
	}
	dt {
		font-weight: 600;
	}
	dd {
		margin: 0;
	}
</style>
