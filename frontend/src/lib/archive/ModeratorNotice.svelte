<script lang="ts">
	import { formatDate } from '#lib/i18n/format.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { archiveContext } from './context.svelte';

	/**
	 * For Moderators only (the API sends these to no one else): a withdrawn record's
	 * banner, stated in words. The legal action log and Reinstate come with Rights and
	 * legal actions.
	 */
	let { withdrawnAt }: { withdrawnAt: string | null | undefined } = $props();
	const context = archiveContext();
</script>

{#if withdrawnAt}
	<p class="banner" role="note">
		{m.archive_withdrawn_banner({ date: formatDate(withdrawnAt, context.dates) })}
	</p>
{/if}

<style>
	.banner {
		border: 2px solid var(--text);
		padding: 0.75rem 1rem;
		font-weight: 600;
	}
</style>
