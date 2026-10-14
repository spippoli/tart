<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import ConditionLine from '#lib/archive/ConditionLine.svelte';
	import ConditionSign from '#lib/archive/ConditionSign.svelte';
	import Content from '#lib/archive/Content.svelte';
	import { archiveContext } from '#lib/archive/context.svelte.ts';
	import RecordAnchor from '#lib/archive/RecordAnchor.svelte';
	import { linkText, recordHref, type Medium, type RecordLink } from '#lib/archive/records.ts';
	import type { components } from '../api/schema';

	/**
	 * One Artwork as a card (Discovery spec, List entries), the same in the side panel,
	 * the Explore list, and `/archivio`: thumbnail, title, Condition word and sign with the
	 * latest documentation date, Attribution summary, and, in the lists, the "where"
	 * line. The title links to the Artwork page; "Show on map" is a second, separate
	 * control, given as a link here and by the Explore view as a button.
	 */
	let {
		entry,
		where = true,
		onmap
	}: {
		entry: components['schemas']['ListEntry'];
		/** The "where" line: in the two lists, not in the panel. */
		where?: boolean;
		/** The "Show on map" control, if the view has one. */
		onmap?: import('svelte').Snippet<[string]>;
	} = $props();
	const context = archiveContext();

	const title = $derived(entry.title ?? m.archive_untitled());
	const thumbnail = $derived(entry.thumbnail);
	const nameOf = (link: RecordLink) => linkText(link, context.surfaceType, context.locale);
	const list = (links: RecordLink[], type: 'conjunction' | 'disjunction') =>
		new Intl.ListFormat(context.locale, { type }).format(links.map(nameOf));
	const attribution = $derived.by(() => {
		if (entry.attributed.length === 0 && entry.disputed.length === 0) {
			return m.archive_unknown_artist();
		}
		const parts: string[] = [];
		if (entry.attributed.length > 0) {
			const names = entry.attributed.map((link) =>
				entry.probable.includes(link.id)
					? m.discovery_entry_probable({ name: nameOf(link) })
					: nameOf(link)
			);
			parts.push(new Intl.ListFormat(context.locale, { type: 'conjunction' }).format(names));
		}
		if (entry.disputed.length > 0) {
			parts.push(m.discovery_entry_disputed({ names: list(entry.disputed, 'disjunction') }));
		}
		return parts.join(' · ');
	});
	const place = $derived(entry.site ?? entry.area);

	const boxWords: Record<Medium, () => string> = {
		text: m.discovery_entry_thumbnail_text,
		link: m.discovery_entry_thumbnail_link,
		pdf: m.discovery_entry_thumbnail_pdf,
		image: m.discovery_entry_thumbnail_image
	};
</script>

<article class="entry" aria-labelledby="entry-{entry.id}">
	<div class="thumbnail">
		{#if thumbnail?.file && (thumbnail.medium === 'image' || thumbnail.medium === 'pdf')}
			{@const size = thumbnail.renditions?.view}
			<img
				src="/api/media/{thumbnail.file}/view"
				alt={thumbnail.medium === 'image'
					? (thumbnail.alt_text ?? '')
					: m.archive_pdf_preview_alt()}
				lang={thumbnail.medium === 'image' ? context.contentLanguage : undefined}
				width={size?.width}
				height={size?.height}
				loading="lazy"
			/>
		{:else if entry.latest_item_medium}
			<p class="box">{boxWords[entry.latest_item_medium]()}</p>
		{:else}
			<p class="box">
				<ConditionSign group={entry.condition.group} />{m.discovery_entry_no_documentation()}
			</p>
		{/if}
	</div>
	<div class="text">
		<h3 id="entry-{entry.id}">
			<a href={recordHref('artwork', entry.path)}
				>{#if entry.title}<Content text={entry.title} />{:else}{title}{/if}</a
			>
		</h3>
		<p class="condition">
			<ConditionLine condition={entry.condition} lastDocumented={entry.last_documented} />
		</p>
		<p class="attribution">{attribution}</p>
		{#if where && (place || entry.approximate)}
			<p class="where">
				{#if place}<RecordAnchor link={place} />{/if}
				{#if entry.approximate}<span class="approximate">({m.discovery_entry_approximate()})</span
					>{/if}
			</p>
		{/if}
		{#if onmap}{@render onmap(title)}{/if}
	</div>
</article>

<style>
	.entry {
		display: grid;
		grid-template-columns: 6rem 1fr;
		gap: 0.75rem;
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--border);
		border-radius: 4px;
	}
	.thumbnail img,
	.box {
		inline-size: 6rem;
		block-size: 6rem;
		box-sizing: border-box;
	}
	.thumbnail img {
		object-fit: cover;
		background: var(--surface);
	}
	.box {
		display: flex;
		align-items: center;
		justify-content: center;
		margin: 0;
		padding: 0.25rem;
		text-align: center;
		font-size: 0.8125rem;
		background: var(--surface);
		border: 1px dashed var(--border);
		overflow-wrap: anywhere;
	}
	.text {
		display: grid;
		gap: 0.15rem;
		align-content: start;
		min-inline-size: 0;
	}
	h3,
	p {
		margin: 0;
	}
	h3 {
		font-size: 1.0625rem;
	}
	.attribution,
	.where {
		color: var(--text-muted);
	}
</style>
