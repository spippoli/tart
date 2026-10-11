<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import { getLocale } from '#lib/paraglide/runtime.js';
	import { formatList, languageName } from '#lib/i18n/format.ts';
	import PageTitle from '#lib/shell/PageTitle.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const locale = $derived(getLocale());
	const dsaLanguages = $derived(
		formatList(
			data.contacts.dsa_languages.map((tag) => languageName(tag, { locale })),
			{ locale }
		)
	);
</script>

<PageTitle title={m.about_contact_title()} />

<h1>{m.about_contact_title()}</h1>

<h2>{m.contact_operator()}</h2>
<!-- A legal name: shown as configured, in the Content language. -->
<p lang={data.contentLanguage}>{data.operatorName}</p>

{#if data.contacts.general}
	<h2>{m.contact_general_heading()}</h2>
	<p>{m.contact_general_text()}</p>
	<p><a href="mailto:{data.contacts.general}">{data.contacts.general}</a></p>
{/if}

<h2>{m.contact_dsa_heading()}</h2>
<p>{m.contact_dsa_text({ languages: dsaLanguages })}</p>
<p><a href="mailto:{data.contacts.dsa}">{data.contacts.dsa}</a></p>

<h2>{m.contact_privacy_heading()}</h2>
<p>{m.contact_privacy_text()}</p>
<p><a href="mailto:{data.contacts.privacy}">{data.contacts.privacy}</a></p>
