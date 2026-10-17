<script lang="ts">
	import { formatUncertainDate, type DateFormatContext } from '#lib/archive/uncertain-date.ts';
	import { m } from '#lib/paraglide/messages.js';
	import type { components } from '../api/schema';

	type Comparison = components['schemas']['ImageComparisonOut'];
	type Side = components['schemas']['ImageSideOut'];

	/**
	 * The proposed image beside the most recent image of the Artwork, at the same size,
	 * current on the left and proposed on the right, stacked below 600 px, each captioned with
	 * its Observed date, Creator credit, and licence; each opens at full size in a new tab
	 * (Contribution and moderation spec, Submission page). There is no swipe or toggle.
	 */
	let {
		comparison,
		context,
		contentLanguage
	}: { comparison: Comparison; context: DateFormatContext; contentLanguage: string } = $props();

	function caption(side: Side): string {
		return m.moderation_images_caption({
			date: formatUncertainDate(side.observed_date as never, context),
			credit: side.creator_credit ?? m.moderation_images_unknown(),
			licence: side.licence ?? m.moderation_images_unknown()
		});
	}
</script>

<div class="pair">
	<figure>
		<figcaption><strong>{m.moderation_images_current()}</strong></figcaption>
		{#if comparison.current}
			<a href="/api/media/{comparison.current.file}/large" target="_blank" rel="noopener">
				<img
					src="/api/media/{comparison.current.file}/view"
					alt={comparison.current.alt_text
						? m.moderation_images_alt_current({ alt: comparison.current.alt_text })
						: m.moderation_images_current()}
					lang={comparison.current.alt_text ? contentLanguage : undefined}
				/>
			</a>
			<p>{caption(comparison.current)}</p>
			<p>
				<a href="/api/media/{comparison.current.file}/large" target="_blank" rel="noopener"
					>{m.moderation_images_full()}</a
				>
			</p>
		{:else}
			<p class="empty">{m.moderation_images_none()}</p>
		{/if}
	</figure>
	<figure>
		<figcaption><strong>{m.moderation_images_proposed()}</strong></figcaption>
		<a href="/api/media/{comparison.proposed.file}/large" target="_blank" rel="noopener">
			<img
				src="/api/media/{comparison.proposed.file}/view"
				alt={comparison.proposed.alt_text
					? m.moderation_images_alt_proposed({ alt: comparison.proposed.alt_text })
					: m.moderation_images_proposed()}
				lang={comparison.proposed.alt_text ? contentLanguage : undefined}
			/>
		</a>
		<p>{caption(comparison.proposed)}</p>
		<p>
			<a href="/api/media/{comparison.proposed.file}/large" target="_blank" rel="noopener"
				>{m.moderation_images_full()}</a
			>
		</p>
	</figure>
</div>

<style>
	/* Side by side at the same size; stacked below 600 px. */
	.pair {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
		max-inline-size: 50rem;
	}

	@media (max-width: 600px) {
		.pair {
			grid-template-columns: 1fr;
		}
	}

	figure {
		margin: 0;
		min-inline-size: 0;
	}

	img {
		display: block;
		inline-size: 100%;
		aspect-ratio: 4 / 3;
		object-fit: contain;
		background: var(--surface);
		border: 2px solid var(--border);
	}

	/* The proposed image is framed with a dashed line: proposed, never shown as accepted. */
	figure:last-child img {
		border: 2px dashed currentColor;
	}

	p {
		margin-block: 0.25rem;
		overflow-wrap: anywhere;
	}

	.empty {
		border: 1px solid var(--border);
		padding: 1rem;
	}
</style>
