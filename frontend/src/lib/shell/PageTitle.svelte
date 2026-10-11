<script lang="ts">
	import { page } from '$app/state';
	import { m } from '#lib/paraglide/messages.js';

	/** The browser title: `<Page> — <Archive name>` (Foundations spec, Layout). */
	let { title }: { title: string } = $props();
</script>

<svelte:head>
	<title>{m.page_title({ page: title, archive: page.data.identity.name })}</title>
</svelte:head>
