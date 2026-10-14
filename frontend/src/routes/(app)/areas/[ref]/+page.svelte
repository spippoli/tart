<script lang="ts">
	import PlacePage from '#lib/archive/PlacePage.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
</script>

<PlacePage place={data.place} />
