<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import PageTitle from '../shell/PageTitle.svelte';
	import ArtworkCards from './ArtworkCards.svelte';
	import Content from './Content.svelte';
	import { archiveContext } from './context.svelte';
	import ModeratorNotice from './ModeratorNotice.svelte';
	import RecordFooter from './RecordFooter.svelte';
	import RedactionMark from './RedactionMark.svelte';
	import LinkList from './LinkList.svelte';
	import { kindWord, type PlaceView } from './records';

	/**
	 * A Site, Area, or Series page (archive-records spec): header, description, the
	 * Locations of its Artworks (the map comes with Discovery), the Artworks with their
	 * Condition, Sources, actions, and the Revisions link.
	 */
	let { place }: { place: PlaceView } = $props();
	const context = archiveContext();
	const redacted = (field: string) => place.redacted_fields?.includes(field) ?? false;
	const title = $derived(place.name ?? m.archive_content_redacted());
	const locations = $derived(
		place.locations.map((location) => ({
			kind: 'location' as const,
			id: location.id,
			path: location.path,
			name: null,
			location_title: location.title
		}))
	);
</script>

<PageTitle {title} />

<article>
	<ModeratorNotice withdrawnAt={place.withdrawn_at} />
	<header>
		<p class="kind">{kindWord(place.kind, context.locale)}</p>
		<h1>
			{#if place.name}<Content text={place.name} />{:else}{title}{/if}
			<RedactionMark redactions={place.redactions} field="name" />
		</h1>
	</header>
	<Content text={place.description} block redacted={redacted('description')} />

	{#if place.kind !== 'series' && locations.length > 0}
		<section aria-labelledby="locations">
			<h2 id="locations">{m.archive_location()}</h2>
			<p><LinkList links={locations} /></p>
		</section>
	{/if}

	<section aria-labelledby="artworks">
		<h2 id="artworks">{m.archive_artworks_heading()}</h2>
		<ArtworkCards cards={place.artworks} empty={m.archive_no_artworks()} />
	</section>

	{#if place.sources.length > 0}
		<section aria-labelledby="sources">
			<h2 id="sources">{m.archive_sources_heading()}</h2>
			<p><LinkList links={place.sources} /></p>
		</section>
	{/if}

	<RecordFooter kind={place.kind} id={place.id} path={place.path} />
</article>

<style>
	.kind {
		color: var(--text-muted);
		margin-block-end: 0;
	}
</style>
