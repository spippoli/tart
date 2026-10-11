<script lang="ts">
	import ContentText from './ContentText.svelte';
	import PageTitle from './PageTitle.svelte';

	/** An About subpage that renders one Operator text, as HTML rendered on the server. */
	let { title, html }: { title: string; html: string } = $props();
</script>

<PageTitle {title} />

<h1>{title}</h1>
<ContentText {html} />
