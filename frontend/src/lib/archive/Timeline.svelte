<script lang="ts">
	import { formatDate } from '#lib/i18n/format.ts';
	import { m } from '#lib/paraglide/messages.js';
	import Citations from './Citations.svelte';
	import Content from './Content.svelte';
	import { archiveContext } from './context.svelte';
	import RecordAnchor from './RecordAnchor.svelte';
	import {
		archiveDate,
		eventWord,
		evidenceWords,
		mediumWord,
		recordHref,
		revisionsHref,
		type ArtworkView,
		type EventEntry,
		type ItemEntry
	} from './records';

	/**
	 * An Artwork's Timeline (criteria 21, 22, 36): a chronologically ordered list of
	 * History events, each with its Observed, submitted, and approved dates and a link to
	 * the Revision that introduced it, and of Documentation items, each with its Observed
	 * date only. No User name appears on it. Undated entries come last, in their group.
	 */
	let { artwork }: { artwork: ArtworkView } = $props();
	const context = archiveContext();
	const groups = $derived(
		[
			{ heading: null, entries: artwork.timeline.dated },
			{ heading: m.archive_timeline_undated(), entries: artwork.timeline.undated }
		].filter((group) => group.entries.length > 0)
	);
	const asEvent = (entry: EventEntry | ItemEntry) => entry as EventEntry;
	const asItem = (entry: EventEntry | ItemEntry) => entry as ItemEntry;
</script>

{#each groups as group, index (index)}
	{#if group.heading}<h3>{group.heading}</h3>{/if}
	<ol class="timeline">
		{#each group.entries as entry (`${entry.entry}-${entry.id}`)}
			<li>
				{#if entry.entry === 'event'}
					{@const event = asEvent(entry)}
					<p class="what">
						<strong>{eventWord(event.type, event.condition, context.locale)}</strong>
						{#if event.covering}
							· {m.archive_covered_by()} <RecordAnchor link={event.covering} />
						{/if}
					</p>
					<dl>
						<dt>{m.archive_timeline_observed()}</dt>
						<dd>{archiveDate(event.observed_date, context.dates)}</dd>
						<dt>{m.archive_timeline_submitted()}</dt>
						<dd>{formatDate(event.submitted_at, context.dates)}</dd>
						<dt>{m.archive_timeline_approved()}</dt>
						<dd>{formatDate(event.approved_at, context.dates)}</dd>
					</dl>
					<p>
						{evidenceWords(event.evidence_level, event.citations.length, context.locale)}
						{#if event.citations.length > 0}· <Citations citations={event.citations} />{/if}
					</p>
					{#if event.note}
						<div class="note">{m.archive_note()}: <Content text={event.note} /></div>
					{/if}
					<p>
						<a href={revisionsHref('artwork', artwork.path, event.revision)}
							>{m.archive_timeline_provenance()}</a
						>
					</p>
				{:else}
					{@const item = asItem(entry)}
					<p class="what">
						<a href={recordHref('documentation_item', item.path)}
							>{m.archive_timeline_item({ medium: mediumWord(item.medium, context.locale) })}</a
						>
					</p>
					<dl>
						<dt>{m.archive_timeline_observed()}</dt>
						<dd>{archiveDate(item.observed_date, context.dates)}</dd>
					</dl>
				{/if}
			</li>
		{/each}
	</ol>
{/each}

<style>
	.timeline {
		padding-inline-start: 1.25rem;
		display: grid;
		gap: 1rem;
	}
	.timeline p {
		margin: 0.15rem 0;
	}
	dl {
		display: grid;
		grid-template-columns: max-content 1fr;
		gap: 0 1rem;
		margin: 0.25rem 0;
	}
	dt {
		color: var(--text-muted);
	}
	dd {
		margin: 0;
	}
</style>
