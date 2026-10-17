<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import FieldInput from './FieldInput.svelte';
	import { jsonToValue, type SiteValue } from './form';
	import type { FieldSpec } from './spec';
	import type { RecordEditorState } from './state.svelte';
	import { currentText, fieldLabel } from './words';

	/**
	 * One field of an existing record (Contribution and moderation spec, Other editors:
	 * "per field: *Edit* reveals current vs proposed"). It says what the record holds now;
	 * *Edit* opens the control on that value, and the proposal is drawn as proposed until it
	 * is approved. *Cancel* takes the field back out of the Submission.
	 */
	let { editor, spec }: { editor: RecordEditorState; spec: FieldSpec } = $props();
	const label = $derived(fieldLabel(spec.name));
	const editing = $derived(spec.name in editor.form.fields);
	const current = $derived(currentText(spec, editor.config.current[spec.name], editor));
	const lang = $derived(
		spec.content && !editor.redacted(spec.name) && editor.config.current[spec.name]
			? editor.config.contentLanguage
			: undefined
	);

	function start() {
		const stored = editor.redacted(spec.name) ? null : editor.config.current[spec.name];
		// A value hidden by a Redaction is never pre-filled; setting the field replaces it.
		editor.form.fields[spec.name] = jsonToValue(spec, stored, (id) => editor.name(id));
	}

	function cancel() {
		const value = editor.form.fields[spec.name] as SiteValue | undefined;
		if (spec.type === 'site' && value?.kind === 'new') {
			const key = value.key;
			editor.form.sites = editor.form.sites.filter((each) => each.key !== key);
		}
		delete editor.form.fields[spec.name];
	}
</script>

<section class="row" aria-labelledby="{spec.name}-row-label">
	<h3 id="{spec.name}-row-label">{label}</h3>
	<p class="current">
		<span class="tag">{m.editor_current()}</span>
		<span {lang}>{current}</span>
	</p>
	{#if editing}
		<div class="proposal">
			<p class="tag"><strong>{m.editor_proposed_label()}</strong></p>
			<FieldInput {editor} {spec} {label} />
			<button type="button" onclick={cancel}>{m.editor_edit_cancel({ field: label })}</button>
		</div>
	{:else}
		<button type="button" onclick={start}>{m.editor_edit_field({ field: label })}</button>
	{/if}
</section>

<style>
	.row {
		display: grid;
		gap: 0.75rem;
		justify-items: start;
		border-block-start: 1px solid var(--border);
		padding-block: 1rem 0.5rem;
	}

	h3,
	p {
		margin: 0;
	}

	.tag {
		font-variant-caps: all-small-caps;
		letter-spacing: 0.04em;
		margin-inline-end: 0.5rem;
	}

	.proposal {
		display: grid;
		gap: 0.75rem;
		justify-items: start;
		inline-size: 100%;
		border: 3px dashed var(--text);
		padding: 1rem;
		background-image: repeating-linear-gradient(
			135deg,
			transparent 0 10px,
			color-mix(in srgb, var(--text) 9%, transparent) 10px 11px
		);
	}

	button {
		min-block-size: 2.75rem;
		padding-inline: 0.75rem;
		background: var(--background);
		color: var(--text);
		border: 1px solid var(--border);
		cursor: pointer;
	}
</style>
