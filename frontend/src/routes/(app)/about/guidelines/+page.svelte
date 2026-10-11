<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import OperatorTextPage from '#lib/shell/OperatorTextPage.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
</script>

<OperatorTextPage title={m.about_guidelines_title()} html={data.html} />
