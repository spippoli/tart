<script lang="ts">
	import RevisionsPage from '#lib/archive/RevisionsPage.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
</script>

<RevisionsPage view={data.view} kind="artwork" />
