<script lang="ts">
	import LinkList from './LinkList.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import type { RecordLink } from './records';

	/** The public Sources and Documentation items a Claim cites. */
	let { citations }: { citations: RecordLink[] } = $props();
</script>

{#if citations.length > 0}
	<span class="citations"
		>{m.archive_citations()}:
		<LinkList links={citations} /></span
	>
{/if}
