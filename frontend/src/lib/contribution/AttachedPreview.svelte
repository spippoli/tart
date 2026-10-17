<script lang="ts">
	import { conditionWord, eventWord, evidenceWords, mediumWord } from '#lib/archive/records.ts';
	import { formatUncertainDate } from '#lib/archive/uncertain-date.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { toUncertainDate } from './date-field';
	import type { Condition } from './form';
	import type { EditorState } from './state.svelte';

	/**
	 * The proposal for an Artwork that exists (Contribution and moderation spec, Common
	 * rules: Preview): the files, the History event and the Sources it adds, hatched with a
	 * dashed outline and labelled as proposed. The Condition the archive displays does not
	 * change until it is approved (ADR 0015).
	 */
	let { editor }: { editor: EditorState } = $props();
	const config = $derived(editor.config);
	const form = $derived(editor.form);
	const event = $derived(form.event);
	const dates = $derived({ locale: config.locale, timeZone: config.timeZone });
	const hasEvent = $derived(editor.flavour === 'event' || event.shows === true);

	function dateWords(field: Parameters<typeof toUncertainDate>[0]): string | null {
		const outcome = toUncertainDate(field, editor.today);
		return 'problem' in outcome || outcome.date === null
			? null
			: formatUncertainDate(outcome.date, dates);
	}

	const cited = $derived(form.documentation.length + form.sources.length);
</script>

<section class="proposed" aria-labelledby="editor-preview-title">
	<h3 id="editor-preview-title">{m.editor_preview_title()}</h3>
	<p class="label"><strong>{m.editor_proposed_label()}</strong></p>

	<dl>
		<dt>{m.editor_preview_artwork_target()}</dt>
		<dd lang={config.contentLanguage}>{form.target?.title || m.archive_untitled()}</dd>

		<dt>{m.editor_preview_documentation()}</dt>
		<dd>
			{#if form.documentation.length === 0}
				{m.editor_preview_none()}
			{:else}
				<ul>
					{#each form.documentation as item (item.key)}
						<li>
							{mediumWord(item.medium, config.locale)}
							{#if dateWords(item.observed)}· {dateWords(item.observed)}{/if}
						</li>
					{/each}
				</ul>
			{/if}
		</dd>

		{#if hasEvent && event.type}
			<dt>{m.editor_preview_event()}</dt>
			<dd>
				{eventWord(event.type, (event.condition || 'unknown') as Condition, config.locale)}
				{#if event.type === 'condition_recorded' && event.condition}
					({conditionWord(event.condition, config.locale)})
				{/if}
				{#if dateWords(event.observed)}· {dateWords(event.observed)}{/if}
				· {evidenceWords(cited > 0 ? 'documented' : 'reported', cited, config.locale)}
			</dd>
			{#if event.covering}
				<dt>{m.editor_preview_covering()}</dt>
				<dd lang={config.contentLanguage}>{event.covering.title}</dd>
			{/if}
			{#if event.note}
				<dt>{m.editor_event_note()}</dt>
				<dd lang={config.contentLanguage}>{event.note}</dd>
			{/if}
		{/if}

		{#if form.sources.length > 0}
			<dt>{m.editor_preview_sources()}</dt>
			<dd>{form.sources.map((each) => each.title).join(', ')}</dd>
		{/if}
	</dl>
</section>

<p class="displayed" data-displayed-condition>
	{m.editor_preview_displayed_condition_existing()}
</p>

<style>
	.proposed {
		border: 3px dashed var(--text);
		padding: 1rem;
		background-image: repeating-linear-gradient(
			135deg,
			transparent 0 10px,
			color-mix(in srgb, var(--text) 9%, transparent) 10px 11px
		);
	}

	.proposed > * {
		margin-block: 0 0.75rem;
	}

	.label {
		font-variant-caps: all-small-caps;
		letter-spacing: 0.04em;
	}

	dl {
		display: grid;
		grid-template-columns: max-content 1fr;
		gap: 0.35rem 1rem;
		margin: 0;
	}

	dt {
		font-weight: 600;
	}

	dd {
		margin: 0;
	}

	ul {
		margin: 0;
		padding-inline-start: 1.25rem;
	}

	.displayed {
		margin: 0.75rem 0 0;
	}

	@media (max-width: 36rem) {
		dl {
			grid-template-columns: 1fr;
		}
	}
</style>
