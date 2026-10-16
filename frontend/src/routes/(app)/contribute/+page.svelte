<script lang="ts">
	import { enhance } from '$app/forms';
	import { errorText } from '#lib/contribution/words.ts';
	import { licence } from '#lib/licences.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { getLocale, localizeHref } from '#lib/paraglide/runtime.js';
	import PageTitle from '#lib/shell/PageTitle.svelte';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();

	const formatContext = $derived({ locale: data.locale, timeZone: data.timeZone });
	const dataLicence = $derived(licence(data.dataLicence, getLocale()));
	const fileLicences = $derived(data.fileLicences.map((each) => licence(each, getLocale())));
	const startError = $derived(
		form && 'code' in form
			? errorText(
					String(form.code),
					'retryAfter' in form ? Number(form.retryAfter) : undefined,
					formatContext
				)
			: undefined
	);
</script>

<PageTitle title={m.contribute_title()} />

<h1>{m.contribute_title()}</h1>
<p class="intro">{m.contribute_intro()}</p>

<section aria-labelledby="start-heading">
	<h2 id="start-heading">{m.contribute_start_heading()}</h2>
	<p>{m.contribute_start_text()}</p>
	{#if startError}
		<p class="error" role="alert"><strong>{startError}</strong></p>
	{/if}
	<form method="post" action="?/start" use:enhance>
		<button type="submit">{m.contribute_start_submit()}</button>
	</form>
</section>

<section aria-labelledby="rules-heading">
	<h2 id="rules-heading">{m.contribute_rules_heading()}</h2>
	{#if data.hasGuidelines}
		<p>
			<a href={localizeHref('/about/guidelines')}>{m.contribute_guidelines_link()}</a>
		</p>
	{/if}
	<p>
		{m.contribute_licence_data({
			licence: m.data_licence_name({ name: dataLicence.name, label: dataLicence.label })
		})}
		<a href={localizeHref('/about/data-licence')}>{m.contribute_licence_link()}</a>
	</p>
	<p>{m.contribute_licence_files()}</p>
	<ul>
		{#each fileLicences as each (each.label)}
			<li><a href={each.url}>{m.data_licence_name({ name: each.name, label: each.label })}</a></li>
		{/each}
	</ul>
</section>

<section aria-labelledby="mine-heading">
	<h2 id="mine-heading">{m.contribute_mine_heading()}</h2>
	<p>{m.contribute_mine_text()}</p>
	<p><a href={localizeHref('/account/contributions')}>{m.user_menu_contributions()}</a></p>
</section>

<style>
	.intro,
	section {
		max-inline-size: 40rem;
	}

	section {
		margin-block-end: 2.5rem;
	}

	button {
		font: inherit;
		color: inherit;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 0.25rem;
		padding: 0.375rem 0.75rem;
		cursor: pointer;
	}

	.error {
		border-inline-start: 4px solid currentColor;
		padding-inline-start: 0.75rem;
	}
</style>
