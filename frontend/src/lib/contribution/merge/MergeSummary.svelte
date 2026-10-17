<script lang="ts">
	import RecordAnchor from '#lib/archive/RecordAnchor.svelte';
	import { archiveContext } from '#lib/archive/context.svelte.ts';
	import { kindWord } from '#lib/archive/records.ts';
	import { m } from '#lib/paraglide/messages.js';
	import type { MergeReview } from './types';

	/**
	 * The records a Merge, Duplicate retirement, or Unmerge Submission involves, for its
	 * Submitter and for the Moderators who decide on it: the folded record, the surviving
	 * one, and the records the approval rewrites (Contribution and moderation spec, Merge,
	 * Duplicate retirement, Unmerge; Submission page).
	 */
	let { review }: { review: MergeReview } = $props();
	const context = archiveContext();
</script>

<section aria-labelledby="merge-summary-heading">
	<h2 id="merge-summary-heading">{m.merge_summary_heading()}</h2>
	<dl>
		<div>
			<dt>{m.merge_summary_folded()}</dt>
			<dd>{kindWord(review.source.kind, context.locale)} <RecordAnchor link={review.source} /></dd>
		</div>
		<div>
			<dt>{m.merge_summary_surviving()}</dt>
			<dd>{kindWord(review.into.kind, context.locale)} <RecordAnchor link={review.into} /></dd>
		</div>
		<div>
			<dt>{m.merge_summary_references()}</dt>
			<dd>
				{#if review.references.length === 0 && review.references_hidden === 0}
					{m.merge_summary_none()}
				{:else}
					<ul>
						{#each review.references as link (link.id)}
							<li>{kindWord(link.kind, context.locale)} <RecordAnchor {link} /></li>
						{/each}
					</ul>
					{#if review.references_hidden > 0}
						<p>{m.merge_references_hidden({ count: review.references_hidden })}</p>
					{/if}
				{/if}
			</dd>
		</div>
	</dl>
</section>

<style>
	dl {
		display: grid;
		gap: 0.5rem;
	}

	dt {
		font-weight: 600;
	}

	dd {
		margin: 0;
	}
</style>
