<script lang="ts">
	import RecordAnchor from './RecordAnchor.svelte';
	import type { RecordLink } from './records';

	/** Record links separated by commas. */
	let { links }: { links: RecordLink[] } = $props();
	const separator = ', ';
</script>

{#each links as link, index (link.id)}{#if index > 0}{separator}{/if}<RecordAnchor {link} />{/each}
