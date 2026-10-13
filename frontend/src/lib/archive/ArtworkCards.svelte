<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import ConditionLine from './ConditionLine.svelte';
	import Content from './Content.svelte';
	import { archiveContext } from './context.svelte';
	import { recordHref, type ArtworkCard } from './records';

	/** Artworks in a list: title, types, and the Condition with its latest documentation. */
	let {
		cards,
		empty = m.archive_none(),
		extra
	}: {
		cards: ArtworkCard[];
		empty?: string;
		extra?: (card: ArtworkCard) => string | null;
	} = $props();
	const context = archiveContext();
</script>

{#if cards.length === 0}
	<p class="empty">{empty}</p>
{:else}
	<ul class="cards">
		{#each cards as card (card.id)}
			<li>
				<a href={recordHref('artwork', card.path)}
					>{#if card.title}<Content text={card.title} />{:else}{m.archive_untitled()}{/if}</a
				>
				<span class="types"
					>{card.expression_types
						.map((key: string) => context.expressionType(key))
						.join(', ')}</span
				>
				{#if extra?.(card)}<span class="extra">{extra(card)}</span>{/if}
				<ConditionLine condition={card.condition} lastDocumented={card.last_documented} />
			</li>
		{/each}
	</ul>
{/if}

<style>
	.cards {
		list-style: none;
		padding: 0;
		display: grid;
		gap: 0.75rem;
	}
	.cards li {
		display: grid;
		gap: 0.15rem;
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--border);
		border-radius: 4px;
	}
	.types,
	.extra,
	.empty {
		color: var(--text-muted);
	}
</style>
