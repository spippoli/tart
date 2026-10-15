<script lang="ts">
	import ArtworkCards from '#lib/archive/ArtworkCards.svelte';
	import Content from '#lib/archive/Content.svelte';
	import { archiveContext } from '#lib/archive/context.svelte.ts';
	import Gallery from '#lib/archive/Gallery.svelte';
	import ModeratorNotice from '#lib/archive/ModeratorNotice.svelte';
	import RecordFooter from '#lib/archive/RecordFooter.svelte';
	import { locationTitleText } from '#lib/archive/records.ts';
	import Where from '#lib/archive/Where.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import PageTitle from '#lib/shell/PageTitle.svelte';
	import type { PageProps } from './$types';

	/**
	 * The Location page (archive-records spec): title, Place description, Surface type,
	 * exact or approximate, Site, Areas, the place in words (the mini-map comes with
	 * Discovery), the stratigraphy most recent first, and the documentation of
	 * disappearances there.
	 */
	let { data }: PageProps = $props();
	const location = $derived(data.location);
	const context = archiveContext();
	const title = $derived(
		locationTitleText(location.id, location.title, context.surfaceType, context.locale)
	);
	const where = $derived({
		location: {
			id: location.id,
			path: location.path,
			title: location.title,
			surface_type: location.surface_type,
			geometry: location.geometry,
			point: location.point,
			approximate: location.approximate,
			uncertainty_radius: location.uncertainty_radius
		},
		location_withdrawn: false,
		site: location.site,
		areas: location.areas,
		nearby: location.nearby
	});
	const counts = $derived.by(() => {
		const found: Partial<Record<'present' | 'unknown' | 'disappeared', number>> = {};
		for (const { condition } of location.stratigraphy) {
			found[condition.group] = (found[condition.group] ?? 0) + 1;
		}
		return found;
	});
</script>

<PageTitle {title} />

<article>
	<ModeratorNotice withdrawnAt={location.withdrawn_at} />
	<header>
		<p class="kind">{m.archive_kind_location()}</p>
		<h1>
			{#if location.title.place_description}<Content
					text={location.title.place_description}
				/>{:else}{title}{/if}
		</h1>
		<p>
			{m.archive_surface_type()}: {context.surfaceType(location.surface_type)} ·
			{location.approximate
				? location.uncertainty_radius
					? m.archive_approximate_radius({ radius: String(location.uncertainty_radius) })
					: m.archive_approximate()
				: m.archive_exact()}
		</p>
	</header>

	<section aria-labelledby="where">
		<h2 id="where">{m.archive_where_heading()}</h2>
		<Where {where} {counts} />
	</section>

	<section aria-labelledby="stratigraphy">
		<h2 id="stratigraphy">{m.archive_stratigraphy_heading()}</h2>
		<ArtworkCards cards={location.stratigraphy} empty={m.archive_no_public_artworks_here()} />
	</section>

	{#if location.disappearances.length > 0}
		<section aria-labelledby="disappearances">
			<h2 id="disappearances">{m.archive_disappearances_heading()}</h2>
			<Gallery items={location.disappearances} />
		</section>
	{/if}

	<RecordFooter kind="location" id={location.id} path={location.path} />
</article>

<style>
	.kind {
		color: var(--text-muted);
		margin-block-end: 0;
	}
</style>
