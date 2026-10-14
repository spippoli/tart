<script lang="ts">
	import LinkList from '#lib/archive/LinkList.svelte';
	import ArtworkCards from '#lib/archive/ArtworkCards.svelte';
	import Citations from '#lib/archive/Citations.svelte';
	import ConditionLine from '#lib/archive/ConditionLine.svelte';
	import Content from '#lib/archive/Content.svelte';
	import { archiveContext } from '#lib/archive/context.svelte.ts';
	import Gallery from '#lib/archive/Gallery.svelte';
	import ModeratorNotice from '#lib/archive/ModeratorNotice.svelte';
	import RecordAnchor from '#lib/archive/RecordAnchor.svelte';
	import RecordFooter from '#lib/archive/RecordFooter.svelte';
	import RedactionMark from '#lib/archive/RedactionMark.svelte';
	import {
		archiveDate,
		attributionSummary,
		certaintyWord,
		evidenceWords
	} from '#lib/archive/records.ts';
	import Timeline from '#lib/archive/Timeline.svelte';
	import Where from '#lib/archive/Where.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import PageTitle from '#lib/shell/PageTitle.svelte';
	import type { PageProps } from './$types';

	/**
	 * The Artwork page (archive-records spec, Public record pages), in the spec's order:
	 * header, gallery, where, description and Attributions, Timeline, Sources, related
	 * Artworks, actions, and the Revisions link.
	 */
	let { data }: PageProps = $props();
	const artwork = $derived(data.artwork);
	const context = archiveContext();
	const redacted = (field: string) => artwork.redacted_fields?.includes(field) ?? false;
	const titleText = $derived(
		artwork.title ?? (redacted('title') ? m.archive_content_redacted() : m.archive_untitled())
	);
	const attributions = $derived([
		...artwork.attribution.attributed,
		...artwork.attribution.disputed
	]);
	const conditionSources = $derived.by(() => {
		const entries = [...artwork.timeline.dated, ...artwork.timeline.undated];
		const event = entries.find(
			(entry) => entry.entry === 'event' && entry.id === artwork.condition.event
		);
		return event && event.entry === 'event' ? event.citations.length : 0;
	});
</script>

<PageTitle title={titleText} />

<article>
	<ModeratorNotice withdrawnAt={artwork.withdrawn_at} />

	<header>
		<h1>
			{#if artwork.title}<Content text={artwork.title} />{:else}{titleText}{/if}
			<RedactionMark redactions={artwork.redactions} field="title" />
		</h1>
		<p class="types">
			{artwork.expression_types.map((key) => context.expressionType(key)).join(', ')}
		</p>
		<p>
			<ConditionLine
				condition={artwork.condition}
				lastDocumented={artwork.last_documented}
				evidence
				sources={conditionSources}
			/>
		</p>
		<p>{attributionSummary(artwork.attribution, context.locale)}</p>
		<p class="dates">
			{artwork.creation
				? m.archive_creation_date({ date: archiveDate(artwork.creation, context.dates) })
				: m.archive_creation_unknown()}
			{#if artwork.first_documentation}
				· {m.archive_first_documented({
					date: archiveDate(artwork.first_documentation, context.dates)
				})}
			{/if}
		</p>
	</header>

	<section aria-labelledby="gallery">
		<h2 id="gallery">{m.archive_gallery_heading()}</h2>
		<Gallery items={artwork.gallery} />
	</section>

	<section aria-labelledby="where">
		<h2 id="where">{m.archive_where_heading()}</h2>
		<Where where={artwork.where} counts={{ [artwork.condition.group]: 1 }} />
		{#if artwork.series.length > 0}
			<p>
				{m.archive_series()}:
				<LinkList links={artwork.series} />
			</p>
		{/if}
	</section>

	<section aria-labelledby="description">
		<h2 id="description">{m.archive_description_heading()}</h2>
		<Content text={artwork.description} block redacted={redacted('description')} />
		<RedactionMark redactions={artwork.redactions} field="description" />

		<h3>{m.archive_attribution_heading()}</h3>
		{#if attributions.length === 0}
			<p>{m.archive_unknown_artist()}</p>
		{:else}
			<ul class="attributions">
				{#each attributions as attribution (attribution.artist.id)}
					<li>
						<RecordAnchor link={attribution.artist} /> — {certaintyWord(
							attribution.certainty,
							context.locale
						)}
						{#if attribution.alias}· {m.archive_alias_used({ alias: attribution.alias })}{/if}
						<br />{evidenceWords(
							attribution.evidence_level,
							attribution.citations.length,
							context.locale
						)}
						{#if attribution.citations.length > 0}· <Citations
								citations={attribution.citations}
							/>{/if}
						{#if attribution.note}
							<br />{m.archive_note()}: <Content text={attribution.note} />
						{/if}
						<RedactionMark
							redactions={artwork.redactions}
							field="attributions"
							item={attribution.artist.id}
						/>
					</li>
				{/each}
			</ul>
		{/if}
	</section>

	<section aria-labelledby="timeline">
		<h2 id="timeline">{m.archive_timeline_heading()}</h2>
		<Timeline {artwork} />
	</section>

	{#if artwork.sources.length > 0}
		<section aria-labelledby="sources">
			<h2 id="sources">{m.archive_sources_heading()}</h2>
			<ul>
				{#each artwork.sources as source (source.id)}
					<li><RecordAnchor link={source} /></li>
				{/each}
			</ul>
		</section>
	{/if}

	<section aria-labelledby="related">
		<h2 id="related">{m.archive_related_heading()}</h2>
		<h3>{m.archive_related_same_location()}</h3>
		<ArtworkCards cards={artwork.related.same_location} />
		<h3>{m.archive_related_same_artist()}</h3>
		<ArtworkCards cards={artwork.related.same_artist} />
		<h3>{m.archive_related_same_series()}</h3>
		<ArtworkCards cards={artwork.related.same_series} />
	</section>

	<RecordFooter kind="artwork" id={artwork.id} path={artwork.path} contribute />
</article>

<style>
	.types,
	.dates {
		color: var(--text-muted);
	}
	.attributions {
		padding-inline-start: 1.25rem;
		display: grid;
		gap: 0.5rem;
	}
</style>
