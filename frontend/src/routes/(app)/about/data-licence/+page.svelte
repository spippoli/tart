<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import { getLocale } from '#lib/paraglide/runtime.js';
	import { licence } from '#lib/licences.ts';
	import PageTitle from '#lib/shell/PageTitle.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const dataLicence = $derived(licence(data.dataLicence, getLocale()));
</script>

<PageTitle title={m.about_data_licence_title()} />

<h1>{m.about_data_licence_title()}</h1>

<p>{m.data_licence_text()}</p>
<p>
	<a href={dataLicence.url}
		>{m.data_licence_name({ name: dataLicence.name, label: dataLicence.label })}</a
	>
</p>
<p>{m.data_licence_scope()}</p>
