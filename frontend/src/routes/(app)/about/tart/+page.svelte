<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import { tartVersion } from '#lib/version.ts';
	import PageTitle from '#lib/shell/PageTitle.svelte';
	import { courtesyCredits } from '#lib/credits.ts';

	// Rendered by the platform in every UI language; the credits come from the
	// third-party asset manifest (ADR 0016).
	const repository = 'https://github.com/spippoli/tart';
	const licenceUrl = 'https://polyformproject.org/licenses/noncommercial/1.0.0';
</script>

<PageTitle title={m.about_tart_title()} />

<h1>{m.about_tart_title()}</h1>

<div class="prose">
	<p>{m.tart_intro()}</p>
	<p>{m.tart_version({ version: tartVersion })}</p>
	<p>{m.tart_licence_text()} <a href={licenceUrl}>{m.tart_licence_name()}</a></p>
	<p>{m.tart_licence_scope()}</p>
	<p><a href={repository}>{m.tart_source_code()}</a></p>

	<h2>{m.tart_credits_heading()}</h2>
	{#if courtesyCredits.length === 0}
		<p>{m.tart_credits_empty()}</p>
	{:else}
		<p>{m.tart_credits_intro()}</p>
		<ul>
			{#each courtesyCredits as credit (credit.path)}
				<li>
					{m.tart_credit_entry({ credit: credit.credit, licence: credit.licence })}
					<a href={credit.source}>{m.tart_credit_source()}</a>
				</li>
			{/each}
		</ul>
	{/if}
</div>
