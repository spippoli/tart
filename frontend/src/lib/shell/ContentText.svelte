<script lang="ts">
	import { page } from '$app/state';
	import { m } from '#lib/paraglide/messages.js';
	import { getLocale } from '#lib/paraglide/runtime.js';
	import { languageName } from '#lib/i18n/format.ts';
	import { textDirection } from '#lib/i18n/language.ts';

	/**
	 * An Operator text in the Content language, never translated, marked with its
	 * own `lang` and `dir` whatever the UI language (ADR 0008). `html` comes from
	 * `#lib/server/markdown`, which escapes raw HTML.
	 */
	let { html }: { html: string } = $props();

	const language = $derived(page.data.contentLanguage as string);
	const uiLanguage = $derived(getLocale());
</script>

{#if language !== uiLanguage}
	<p class="note">
		{m.content_language_note({ language: languageName(language, { locale: uiLanguage }) })}
	</p>
{/if}
<div class="prose" lang={language} dir={textDirection(language)}>
	<!-- eslint-disable-next-line svelte/no-at-html-tags -- rendered by micromark, which escapes raw HTML -->
	{@html html}
</div>

<style>
	.note {
		color: var(--text-muted);
		font-style: italic;
	}
</style>
