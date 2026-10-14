<script lang="ts">
	import ArtworkCards from '#lib/archive/ArtworkCards.svelte';
	import Content from '#lib/archive/Content.svelte';
	import { archiveContext } from '#lib/archive/context.svelte.ts';
	import LinkList from '#lib/archive/LinkList.svelte';
	import ModeratorNotice from '#lib/archive/ModeratorNotice.svelte';
	import RecordAnchor from '#lib/archive/RecordAnchor.svelte';
	import RecordFooter from '#lib/archive/RecordFooter.svelte';
	import RedactionMark from '#lib/archive/RedactionMark.svelte';
	import { archivePeriod, certaintyWord, type ArtworkCard } from '#lib/archive/records.ts';
	import { m } from '#lib/paraglide/messages.js';
	import PageTitle from '#lib/shell/PageTitle.svelte';
	import type { PageProps } from './$types';

	/**
	 * The Artist page (archive-records spec): name, kind, Aliases, period of activity,
	 * biography, Areas of activity, Crew memberships both ways, the attributed Artworks
	 * with their certainty in words, Sources, actions. No image of the person.
	 */
	let { data }: PageProps = $props();
	const artist = $derived(data.artist);
	const context = archiveContext();
	const redacted = (field: string) => artist.redacted_fields?.includes(field) ?? false;
	const title = $derived(artist.name ?? m.archive_content_redacted());
	const period = $derived(artist.period ? archivePeriod(artist.period, context.dates) : null);
	const certainties = $derived(
		new Map(artist.artworks.map((entry) => [entry.artwork.id, entry.certainty]))
	);
	const certainty = (card: ArtworkCard) => {
		const found = certainties.get(card.id);
		return found ? certaintyWord(found, context.locale) : null;
	};
</script>

<PageTitle {title} />

<article>
	<ModeratorNotice withdrawnAt={artist.withdrawn_at} />
	<header>
		<p class="kind">
			{artist.artist_kind === 'collective'
				? m.archive_artist_collective()
				: m.archive_artist_individual()}
		</p>
		<h1>
			{#if artist.name}<Content text={artist.name} />{:else}{title}{/if}
			<RedactionMark redactions={artist.redactions} field="name" />
		</h1>
		{#if artist.aliases.length > 0}
			<p>{m.archive_aliases()}: <Content text={artist.aliases.join(', ')} /></p>
		{/if}
		{#if period}<p>{m.archive_period()}: {period}</p>{/if}
	</header>

	{#if artist.biography || redacted('biography')}
		<section aria-labelledby="biography">
			<h2 id="biography">{m.archive_biography_heading()}</h2>
			<Content text={artist.biography} block redacted={redacted('biography')} />
		</section>
	{/if}

	{#if artist.areas.length > 0}
		<p>{m.archive_areas_of_activity()}: <LinkList links={artist.areas} /></p>
	{/if}

	{#if artist.collectives.length > 0}
		<section aria-labelledby="member-of">
			<h2 id="member-of">{m.archive_member_of()}</h2>
			<ul>
				{#each artist.collectives as membership, index (index)}
					<li>
						<RecordAnchor link={membership.artist} />
						{#if membership.period}({archivePeriod(membership.period, context.dates)}){/if}
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	{#if artist.members.length > 0}
		<section aria-labelledby="members">
			<h2 id="members">{m.archive_members()}</h2>
			<ul>
				{#each artist.members as membership, index (index)}
					<li>
						<RecordAnchor link={membership.artist} />
						{#if membership.period}({archivePeriod(membership.period, context.dates)}){/if}
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	<section aria-labelledby="artworks">
		<h2 id="artworks">{m.archive_artworks_heading()}</h2>
		<ArtworkCards
			cards={artist.artworks.map((entry) => entry.artwork)}
			empty={m.archive_no_artworks()}
			extra={certainty}
		/>
	</section>

	{#if artist.sources.length > 0}
		<section aria-labelledby="sources">
			<h2 id="sources">{m.archive_sources_heading()}</h2>
			<p><LinkList links={artist.sources} /></p>
		</section>
	{/if}

	<RecordFooter kind="artist" id={artist.id} path={artist.path} />
</article>

<style>
	.kind {
		color: var(--text-muted);
		margin-block-end: 0;
	}
</style>
