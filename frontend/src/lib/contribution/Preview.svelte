<script lang="ts">
	import {
		certaintyWord,
		conditionWord,
		evidenceWords,
		mediumWord,
		vocabularyLabels
	} from '#lib/archive/records.ts';
	import { formatUncertainDate } from '#lib/archive/uncertain-date.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { toUncertainDate } from './date-field';
	import type { Condition } from './form';
	import type { EditorState } from './state.svelte';

	/**
	 * The proposal as the archive would show it (Contribution and moderation spec, Common
	 * rules: Preview): everything proposed is drawn hatched, with a dashed outline and the
	 * words "Proposed · not public until approved", never by colour alone. The Condition
	 * the archive displays for this Artwork is shown apart and does not change until it is
	 * approved (ADR 0015).
	 */
	let { editor }: { editor: EditorState } = $props();
	const config = $derived(editor.config);
	const form = $derived(editor.form);
	const surfaceLabel = $derived(vocabularyLabels(config.surfaceTypes, config.locale));
	const typeLabel = $derived(vocabularyLabels(config.expressionTypes, config.locale));
	const dates = $derived({ locale: config.locale, timeZone: config.timeZone });

	const place = $derived.by(() => {
		const { existing, geometry, surfaceType, approximate, radius } = form.location;
		if (existing) return existing.title;
		if (!geometry) return null;
		const shape =
			geometry.type === 'Point'
				? m.draw_shape_point()
				: geometry.type === 'LineString'
					? m.draw_shape_line()
					: m.draw_shape_polygon();
		const surface = surfaceType ? `${surfaceLabel(surfaceType)} · ${shape}` : shape;
		const near = approximate ? m.editor_preview_approximate({ radius: radius ?? 0 }) : '';
		return `${surface}${near}`;
	});

	function dateWords(field: Parameters<typeof toUncertainDate>[0]): string | null {
		const outcome = toUncertainDate(field, editor.today);
		return 'problem' in outcome || outcome.date === null
			? null
			: formatUncertainDate(outcome.date, dates);
	}

	const attributions = $derived(
		form.attributed
			? form.attributions.map((each) => ({
					key: each.key,
					name: each.artist?.name ?? '',
					certainty: each.certainty ? certaintyWord(each.certainty, config.locale) : '',
					evidence: evidenceWords(
						each.citations.length > 0 ? 'documented' : 'reported',
						each.citations.length,
						config.locale
					)
				}))
			: []
	);
	const created = $derived(dateWords(form.created.date));
</script>

<section class="proposed" aria-labelledby="editor-preview-title">
	<h3 id="editor-preview-title">{m.editor_preview_title()}</h3>
	<p class="label"><strong>{m.editor_proposed_label()}</strong></p>

	<dl>
		<dt>{m.editor_preview_title_label()}</dt>
		<dd lang={form.untitled || !form.title ? config.locale : config.contentLanguage}>
			{form.untitled || !form.title ? m.archive_untitled() : form.title}
		</dd>

		<dt>{m.editor_preview_types()}</dt>
		<dd>{form.expressionTypes.map(typeLabel).join(', ')}</dd>

		{#if form.description}
			<dt>{m.editor_preview_description()}</dt>
			<dd lang={config.contentLanguage}>{form.description}</dd>
		{/if}

		<dt>{m.editor_preview_location()}</dt>
		<dd>{place ?? m.editor_preview_none()}</dd>

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

		<dt>{m.editor_preview_initial_condition()}</dt>
		<dd>
			{form.initialCondition
				? conditionWord(form.initialCondition as Condition, config.locale)
				: m.editor_preview_none()}
		</dd>

		<dt>{m.editor_preview_attribution()}</dt>
		<dd>
			{#if form.attributed === false}
				{m.archive_unknown_artist()}
			{:else if attributions.length === 0}
				{m.editor_preview_none()}
			{:else}
				<ul>
					{#each attributions as each (each.key)}
						<li>{each.name} · {each.certainty} · {each.evidence}</li>
					{/each}
				</ul>
			{/if}
		</dd>

		{#if created}
			<dt>{m.editor_preview_created()}</dt>
			<dd>{created}</dd>
		{/if}

		{#if form.sources.length > 0}
			<dt>{m.editor_preview_sources()}</dt>
			<dd>{form.sources.map((each) => each.title).join(', ')}</dd>
		{/if}
	</dl>
</section>

<p class="displayed" data-displayed-condition>
	{m.editor_preview_displayed_condition()}
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
