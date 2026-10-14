<script lang="ts">
	import IndexList from '#lib/archive/IndexList.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
</script>

<IndexList index={data.index} title={m.archive_index_series()} />
