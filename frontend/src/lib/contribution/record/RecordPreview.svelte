<script lang="ts">
	import { certaintyWord, kindWord } from '#lib/archive/records.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { valueToJson } from './form';
	import { SPECS } from './spec';
	import type { RecordEditorState } from './state.svelte';
	import { collectionLabel, currentText, describeJson, fieldLabel } from './words';

	/**
	 * The proposal as the archive would show it (Contribution and moderation spec, Common
	 * rules: Preview): everything proposed is drawn hatched, with a dashed outline and the
	 * words "Proposed · not public until approved", never by colour alone. In an edit each
	 * field says what it was and what it becomes; the record keeps showing what it shows now.
	 */
	let { editor }: { editor: RecordEditorState } = $props();
	const form = $derived(editor.form);
	const spec = $derived(SPECS[editor.kind]);
	const medium = $derived(String(editor.config.current.medium ?? ''));

	const rows = $derived.by(() => {
		const out: { label: string; text: string; lang?: string }[] = [];
		for (const field of spec.fields) {
			if (field.media && !field.media.includes(medium)) continue;
			if (!(field.name in form.fields)) continue;
			const proposed = describeJson(
				field,
				valueToJson(field, form.fields[field.name], editor.today),
				editor
			);
			const text = editor.creating
				? proposed
				: m.editor_preview_change({
						from: currentText(field, editor.config.current[field.name], editor),
						to: proposed
					});
			out.push({
				label: fieldLabel(field.name),
				text,
				lang: field.content ? editor.config.contentLanguage : undefined
			});
		}
		return out;
	});

	const items = $derived.by(() => {
		const out: { label: string; adds: string[]; removes: string[] }[] = [];
		for (const collection of spec.collections) {
			const adds: string[] = [];
			const removes: string[] = [];
			const name = collection.name;
			if (collection.type === 'links') {
				const delta = form.links[name];
				adds.push(...(delta?.added ?? []).map((each) => each.name));
				removes.push(...(delta?.removed ?? []).map((id) => editor.name(id)));
				if (collection.picker === 'sources') adds.push(...form.sources.map((each) => each.title));
			} else if (collection.type === 'aliases') {
				adds.push(...form.aliases.added);
				removes.push(...form.aliases.removed);
			} else if (collection.type === 'attributions') {
				const words = (artist: string, certainty: string) =>
					certainty
						? `${artist} · ${certaintyWord(certainty as 'confirmed', editor.config.locale)}`
						: artist;
				adds.push(
					...form.attributions.added.map((each) => words(each.artist?.name ?? '', each.certainty))
				);
				adds.push(
					...Object.values(form.attributions.changed).map((each) =>
						words(each.artist?.name ?? '', each.certainty)
					)
				);
				removes.push(...form.attributions.removed.map((id) => editor.name(id)));
			} else {
				adds.push(...form.crew.added.map((each) => each.collective?.name ?? ''));
				const current = Array.isArray(editor.config.current[name])
					? (editor.config.current[name] as { collective: number }[])
					: [];
				removes.push(
					...form.crew.removed.map((index) => editor.name(current[index]?.collective ?? 0))
				);
			}
			if (adds.length + removes.length > 0)
				out.push({ label: collectionLabel(name), adds, removes });
		}
		return out;
	});

	const created = $derived([
		...form.sites.map((each) => ({
			kind: kindWord('site', editor.config.locale),
			name: each.name
		})),
		...form.series.map((each) => ({
			kind: kindWord('series', editor.config.locale),
			name: each.name
		})),
		...form.artists.map((each) => ({
			kind: kindWord('artist', editor.config.locale),
			name: each.name
		})),
		...form.sources.map((each) => ({
			kind: kindWord('source', editor.config.locale),
			name: each.title
		}))
	]);
</script>

<section class="proposed" aria-labelledby="editor-preview-title">
	<h3 id="editor-preview-title">{m.editor_preview_title()}</h3>
	<p class="label"><strong>{m.editor_proposed_label()}</strong></p>

	<dl>
		{#each rows as row (row.label)}
			<dt>{row.label}</dt>
			<dd lang={row.lang}>{row.text}</dd>
		{/each}
		{#each items as item (item.label)}
			<dt>{item.label}</dt>
			<dd>
				<ul>
					{#each item.adds as added (added)}
						<li>{m.editor_preview_adds({ name: added })}</li>
					{/each}
					{#each item.removes as removed (removed)}
						<li>{m.editor_preview_removes({ name: removed })}</li>
					{/each}
				</ul>
			</dd>
		{/each}
		{#if created.length > 0}
			<dt>{m.editor_preview_creates()}</dt>
			<dd>
				<ul>
					{#each created as each, index (index)}
						<li>{each.kind} · {each.name}</li>
					{/each}
				</ul>
			</dd>
		{/if}
	</dl>
</section>

<p class="displayed">{m.editor_preview_record_unchanged()}</p>

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
