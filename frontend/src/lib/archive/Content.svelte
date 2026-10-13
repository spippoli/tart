<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import { textDirection } from '#lib/i18n/language.ts';
	import { archiveContext } from './context.svelte';

	/**
	 * Archive content (a title, a description, a note): in the Content language, or in
	 * its own `language` tag, with `lang` and `dir`, whatever the UI language (ADR 0008).
	 * A value hidden by a Redaction shows the neutral placeholder, in the UI language.
	 */
	let {
		text,
		language,
		block = false,
		redacted = false
	}: {
		text: string | null | undefined;
		language?: string | null;
		block?: boolean;
		redacted?: boolean;
	} = $props();
	const context = archiveContext();
	const lang = $derived(language ?? context.contentLanguage);
</script>

{#if redacted}
	<span class="redacted">{m.archive_content_redacted()}</span>
{:else if text}
	{#if block}
		<p {lang} dir={textDirection(lang)} class="content">{text}</p>
	{:else}
		<span {lang} dir={textDirection(lang)}>{text}</span>
	{/if}
{/if}

<style>
	.content {
		white-space: pre-line;
	}
	.redacted {
		font-style: italic;
		color: var(--text-muted);
	}
</style>
