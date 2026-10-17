<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import { localizeHref } from '#lib/paraglide/runtime.js';
	import type { Snippet } from 'svelte';
	import { errorText } from './errors';
	import Field from './Field.svelte';
	import type { Session } from './session';
	import { ids } from './validate';

	/**
	 * Review and submit (Contribution and moderation spec, Form structure and Terms of
	 * use): the preview in the editorial label, the optional note to Moderators (never
	 * public), and the acceptance of the terms only when the User has not accepted the
	 * current version. Submitting is Editor's.
	 */
	let {
		editor,
		onsubmit,
		children
	}: {
		editor: Session;
		onsubmit: () => void;
		/** The preview of what is proposed, in the editorial label. */
		children: Snippet;
	} = $props();
	const terms = $derived(editor.config.terms);
	const termsError = $derived(editor.errorAt(ids.terms));
	const termsLink = $derived(localizeHref('/about/terms'));
</script>

<div class="step">
	{@render children()}

	<Field id="editor-note" label={m.editor_review_note()} hint={m.editor_review_note_hint()}>
		{#snippet children(props)}
			<textarea {...props} rows="3" bind:value={editor.note}></textarea>
		{/snippet}
	</Field>

	{#if terms.acceptanceRequired}
		<div class="terms">
			<label>
				<input
					id={ids.terms}
					type="checkbox"
					bind:checked={editor.termsAccepted}
					aria-invalid={termsError ? 'true' : undefined}
					aria-describedby={termsError ? `${ids.terms}-error` : undefined}
				/>
				<span>
					{m.editor_review_accept()}
					<a href={termsLink} target="_blank" rel="noopener">
						{m.editor_review_terms({ version: terms.version })}
						<span class="visually-hidden">{m.editor_new_tab()}</span>
					</a>
				</span>
			</label>
			<p class="hint">{m.editor_review_accept_hint()}</p>
			{#if termsError}
				<p id="{ids.terms}-error" class="error">
					<strong>{m.editor_error_prefix()}</strong>
					{errorText(termsError.code, termsError.params)}
				</p>
			{/if}
		</div>
	{:else}
		<p class="accepted">
			{m.editor_review_accepted({ version: terms.acceptedVersion ?? terms.version })}
			<a href={termsLink} target="_blank" rel="noopener">
				{m.editor_review_read_terms()}
				<span class="visually-hidden">{m.editor_new_tab()}</span>
			</a>
		</p>
	{/if}

	<div class="actions">
		<button
			id="editor-submit"
			type="button"
			class="primary"
			onclick={onsubmit}
			disabled={editor.submitting}
		>
			{editor.submitting ? m.editor_submitting() : m.editor_submit()}
		</button>
	</div>
</div>

<style>
	.step {
		display: grid;
		gap: 1.25rem;
	}

	.terms,
	.accepted {
		display: grid;
		gap: 0.35rem;
		margin: 0;
	}

	.terms label {
		display: flex;
		gap: 0.5rem;
		align-items: baseline;
		font-weight: 600;
	}

	.hint {
		margin: 0;
		color: var(--text-muted);
	}

	.error {
		margin: 0;
		border-inline-start: 4px solid var(--accent, currentColor);
		padding-inline-start: 0.5rem;
	}

	button {
		min-block-size: 2.75rem;
		padding-inline: 1rem;
		background: var(--background);
		color: var(--text);
		border: 1px solid var(--border);
		cursor: pointer;
	}

	.primary {
		font-weight: 600;
		border: 2px solid var(--text);
	}

	button:disabled {
		cursor: default;
		opacity: 0.6;
	}
</style>
