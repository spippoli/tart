<script lang="ts">
	import type { Snippet } from 'svelte';
	import { m } from '#lib/paraglide/messages.js';

	/**
	 * A fieldset (radio buttons, checkboxes, a date) with its hint and its error, the
	 * error being text bound to the group with `aria-describedby`. `invalid` is for the
	 * first control to carry as `aria-invalid`.
	 */
	let {
		id,
		legend,
		hint,
		error,
		radiogroup = false,
		children
	}: {
		id: string;
		legend: string;
		hint?: string;
		error?: string | null;
		/** A group of radio buttons: the group itself, not a button, is what is invalid. */
		radiogroup?: boolean;
		children: Snippet<[{ invalid: 'true' | undefined }]>;
	} = $props();

	const describedby = $derived(
		[hint ? `${id}-hint` : '', error ? `${id}-error` : ''].filter(Boolean).join(' ') || undefined
	);
</script>

<fieldset
	role={radiogroup ? 'radiogroup' : undefined}
	aria-invalid={radiogroup && error ? 'true' : undefined}
	aria-describedby={describedby}
>
	<legend>{legend}</legend>
	{#if hint}<p id="{id}-hint" class="hint">{hint}</p>{/if}
	{@render children({ invalid: error ? 'true' : undefined })}
	{#if error}
		<p id="{id}-error" class="error"><strong>{m.editor_error_prefix()}</strong> {error}</p>
	{/if}
</fieldset>

<style>
	fieldset {
		display: grid;
		gap: 0.5rem;
		justify-items: start;
		border: 1px solid var(--border);
		margin: 0;
		padding: 0.75rem 1rem;
	}

	legend {
		font-weight: 600;
		padding-inline: 0.25rem;
	}

	.hint,
	.error {
		margin: 0;
		max-inline-size: var(--measure);
	}

	.hint {
		color: var(--text-muted);
	}

	.error {
		border-inline-start: 4px solid var(--accent, currentColor);
		padding-inline-start: 0.5rem;
	}

	fieldset :global(label) {
		display: flex;
		gap: 0.5rem;
		align-items: baseline;
	}
</style>
