<script lang="ts">
	import { textDirection } from '#lib/i18n/language.ts';
	import { archiveContext } from './context.svelte';
	import { linkText, recordHref, type RecordLink } from './records';

	/** A link to a record page, named by the record in the Content language. */
	let { link }: { link: RecordLink } = $props();
	const context = archiveContext();
	// A name is archive content; the fallbacks ("Untitled", "Location 12") are UI text.
	const content = $derived(
		link.kind === 'location' ? !!link.location_title?.place_description : !!link.name
	);
</script>

<a
	href={recordHref(link.kind, link.path)}
	lang={content ? context.contentLanguage : undefined}
	dir={content ? textDirection(context.contentLanguage) : undefined}
	>{linkText(link, context.surfaceType, context.locale)}</a
>
