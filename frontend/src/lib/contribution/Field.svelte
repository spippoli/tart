<script lang="ts">
	import type { Snippet } from 'svelte';
	import { m } from '#lib/paraglide/messages.js';

	/**
	 * A labelled control with its hint and its error (Contribution and moderation spec,
	 * Common rules): the error is text, bound to the control with `aria-describedby`,
	 * which also sets `aria-invalid`. The control is given what it needs to carry.
	 */
	let {
		id,
		label,
		hint,
		error,
		lang,
		children
	}: {
		id: string;
		label: string;
		hint?: string;
		error?: string | null;
		/** Marks the label's language when it is archive content. */
		lang?: string;
		children: Snippet<
			[
				{
					id: string;
					'aria-describedby': string | undefined;
					'aria-invalid': 'true' | undefined;
				}
			]
		>;
	} = $props();

	const describedby = $derived(
		[hint ? `${id}-hint` : '', error ? `${id}-error` : ''].filter(Boolean).join(' ') || undefined
	);
</script>

<div class="field">
	<label for={id} {lang}>{label}</label>
	{#if hint}<p id="{id}-hint" class="hint">{hint}</p>{/if}
	{@render children({
		id,
		'aria-describedby': describedby,
		'aria-invalid': error ? 'true' : undefined
	})}
	{#if error}
		<p id="{id}-error" class="error"><strong>{m.editor_error_prefix()}</strong> {error}</p>
	{/if}
</div>

<style>
	.field {
		display: grid;
		gap: 0.35rem;
		justify-items: start;
	}

	label {
		font-weight: 600;
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

	.field :global(input:not([type='checkbox'], [type='radio'], [type='file'])),
	.field :global(select),
	.field :global(textarea) {
		inline-size: min(100%, 36rem);
	}
</style>
