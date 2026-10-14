<script lang="ts">
	import DiscoveryView from '#lib/discovery/DiscoveryView.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import PageTitle from '#lib/shell/PageTitle.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
</script>

<PageTitle title={m.nav_archive()} />

<h1>{m.nav_archive()}</h1>
<DiscoveryView {data} view="archive" heading={m.discovery_list_label()} />
