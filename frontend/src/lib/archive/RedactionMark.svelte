<script lang="ts">
	import type { components } from '../api/schema';
	import { formatDate } from '#lib/i18n/format.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { archiveContext } from './context.svelte';

	/** For Moderators: "Redacted on [date]" beside a value the public cannot see. */
	let {
		redactions,
		field,
		item
	}: {
		redactions: components['schemas']['Redaction'][] | undefined;
		field: string;
		item?: unknown;
	} = $props();
	const context = archiveContext();
	const found = $derived(
		redactions?.find((r) => r.field === field && (item === undefined || r.item === item))
	);
</script>

{#if found}
	<span class="mark"
		>({m.archive_redacted_marker({ date: formatDate(found.redacted_at, context.dates) })})</span
	>
{/if}

<style>
	.mark {
		font-style: italic;
	}
</style>
