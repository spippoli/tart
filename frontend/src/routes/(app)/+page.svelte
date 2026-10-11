<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import { localizeHref } from '#lib/paraglide/runtime.js';
	import { textDirection } from '#lib/i18n/language.ts';
	import PageTitle from '#lib/shell/PageTitle.svelte';
	import type { PageProps } from './$types';

	// The intro band of Explore; the Discovery spec adds the filters, the map, and the list.
	let { data }: PageProps = $props();
	const language = $derived(data.contentLanguage);
</script>

<PageTitle title={m.nav_explore()} />

<section class="intro">
	<h1 lang={language} dir={textDirection(language)}>{data.identity.name}</h1>
	<p class="prose" lang={language} dir={textDirection(language)}>{data.identity.description}</p>
	<p><a href={localizeHref('/about')}>{m.nav_about()}</a></p>
</section>
