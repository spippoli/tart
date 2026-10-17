<script lang="ts">
	import { enhance, type SubmitFunction } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import { errorText } from '#lib/contribution/words.ts';
	import { formatDateTime, type FormatContext } from '#lib/i18n/format.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { localizeHref } from '#lib/paraglide/runtime.js';
	import type { components } from '../api/schema';
	import { CHECKLIST } from './words';

	type Submission = components['schemas']['SubmissionOut'];
	type Reason = { key: string; label: Record<string, string> };
	/** What the page's actions answer: which section failed or finished, with its code. */
	type Outcome = { section?: string; code?: string; retryAfter?: number; done?: string } | null;

	/**
	 * What only a Moderator sees on the Submission page (Contribution and moderation spec,
	 * Submission page, Moderator identity and Moderation notes): the Moderation notes, the
	 * review checklist beside the decision form, and the decision form with the configured
	 * reasons in file order and the platform's "duplicate" last.
	 */
	let {
		submission,
		reasons,
		context,
		contentLanguage,
		own,
		outcome
	}: {
		submission: Submission;
		reasons: Reason[];
		context: FormatContext;
		contentLanguage: string;
		own: boolean;
		outcome: Outcome;
	} = $props();

	const decisions = $derived(submission.decisions);
	const asksMessage = $derived(
		decisions.includes('reject') || decisions.includes('request_changes')
	);
	const noteOutcome = $derived(outcome?.section === 'note' ? outcome : null);
	const decisionOutcome = $derived(outcome?.section === 'decision' ? outcome : null);
	const decisionError = $derived(
		decisionOutcome?.code ? errorText(decisionOutcome.code, undefined, context) : undefined
	);
	const noteError = $derived(
		noteOutcome?.code ? errorText(noteOutcome.code, undefined, context) : undefined
	);
	const reasonInvalid = $derived(decisionOutcome?.code === 'moderation.decision_reason_required');
	const textInvalid = $derived(decisionOutcome?.code === 'moderation.decision_text_required');

	function reasonLabel(entry: Reason): string {
		return entry.label[context.locale] ?? entry.label[contentLanguage] ?? entry.key;
	}

	const decisionButtons: Record<string, () => string> = {
		approve: m.moderation_decision_approve,
		request_changes: m.moderation_decision_request_changes,
		reject: m.moderation_decision_reject
	};
	const doneWords: Record<string, () => string> = {
		approve: m.moderation_decision_done_approve,
		reject: m.moderation_decision_done_reject,
		request_changes: m.moderation_decision_done_request_changes
	};

	/** A decision somebody else took first leaves this page stale: it reloads, with the message. */
	const reloadWhenDecided: SubmitFunction = () => async (result) => {
		await result.update();
		if (result.result.type === 'failure') {
			const code = (result.result.data as { code?: string } | undefined)?.code;
			if (code === 'moderation.already_decided') await invalidateAll();
		}
	};

	function authorText(author: { number: number; display_name: string }): string {
		return m.contribution_actor_named_moderator({
			name: author.display_name,
			number: author.number
		});
	}
</script>

<section aria-labelledby="moderation-heading" class="panel">
	<h2 id="moderation-heading">{m.moderation_panel_heading()}</h2>

	<section aria-labelledby="notes-heading">
		<h3 id="notes-heading">{m.moderation_notes_heading()}</h3>
		<p class="hint">{m.moderation_notes_intro()}</p>
		{#if submission.notes.length === 0}
			<p>{m.moderation_notes_empty()}</p>
		{:else}
			<ol class="notes">
				{#each submission.notes as note, index (index)}
					<li>
						<p class="meta">
							{m.moderation_notes_by({
								author: authorText(note.author),
								date: formatDateTime(note.at, context)
							})}
						</p>
						<blockquote lang={contentLanguage}>{note.text}</blockquote>
					</li>
				{/each}
			</ol>
		{/if}
		<p role="status">{noteOutcome?.done ? m.moderation_notes_done() : ''}</p>
		{#if noteError}
			<p class="error" id="note-error" role="alert"><strong>{noteError}</strong></p>
		{/if}
		<form method="post" action="?/note" use:enhance>
			<label for="note-text">{m.moderation_notes_label()}</label>
			<textarea
				id="note-text"
				name="text"
				rows="3"
				lang={contentLanguage}
				aria-invalid={noteError ? 'true' : undefined}
				aria-describedby={noteError ? 'note-error' : undefined}></textarea>
			<button type="submit">{m.moderation_notes_submit()}</button>
		</form>
	</section>

	<div class="decide">
		<section aria-labelledby="checklist-heading">
			<h3 id="checklist-heading">{m.moderation_checklist_heading()}</h3>
			<p class="hint">{m.moderation_checklist_intro()}</p>
			<ol class="checklist">
				{#each CHECKLIST as item, index (index)}
					<li>{item()}</li>
				{/each}
			</ol>
			<p><a href={localizeHref('/about/guidelines')}>{m.moderation_checklist_guidelines()}</a></p>
		</section>

		<section aria-labelledby="moderation-decision-heading">
			<h3 id="moderation-decision-heading">{m.moderation_decision_heading()}</h3>
			<p role="status">
				{decisionOutcome?.done ? (doneWords[decisionOutcome.done]?.() ?? '') : ''}
			</p>
			{#if decisionError}
				<p class="error" id="decision-error" role="alert"><strong>{decisionError}</strong></p>
			{/if}
			{#if decisions.length === 0}
				<p>
					{#if own}
						{m.moderation_own_notice()}
					{:else}
						{m.moderation_decision_none()}
					{/if}
				</p>
			{:else}
				{#if submission.status === 'changes_requested'}
					<p>{m.moderation_decision_changes_requested()}</p>
				{:else if submission.outdated.length > 0}
					<p>{m.moderation_decision_outdated()}</p>
				{/if}
				<form method="post" action="?/decide" use:enhance={reloadWhenDecided}>
					<input type="hidden" name="version" value={submission.version} />
					{#if asksMessage}
						<label for="decision-reason">{m.moderation_decision_reason_label()}</label>
						<select
							id="decision-reason"
							name="reason"
							aria-invalid={reasonInvalid ? 'true' : undefined}
							aria-describedby={reasonInvalid ? 'decision-error' : undefined}
						>
							<option value="">{m.moderation_decision_reason_choose()}</option>
							{#each reasons as entry (entry.key)}
								<option value={entry.key}>{reasonLabel(entry)}</option>
							{/each}
						</select>
						<label for="decision-text">{m.moderation_decision_text_label()}</label>
						<p class="hint" id="decision-text-hint">{m.moderation_decision_text_hint()}</p>
						<textarea
							id="decision-text"
							name="text"
							rows="4"
							lang={contentLanguage}
							aria-invalid={textInvalid ? 'true' : undefined}
							aria-describedby={textInvalid
								? 'decision-error decision-text-hint'
								: 'decision-text-hint'}></textarea>
					{/if}
					{#if decisions.includes('approve')}
						<p class="hint">{m.moderation_decision_approve_hint()}</p>
					{/if}
					<p class="buttons">
						{#each decisions as verdict (verdict)}
							<button type="submit" name="verdict" value={verdict} formnovalidate
								>{decisionButtons[verdict]()}</button
							>
						{/each}
					</p>
				</form>
			{/if}
		</section>
	</div>
</section>

<style>
	.panel {
		max-inline-size: 60rem;
		margin-block-end: 2rem;
		padding: 0.5rem 1rem 1rem;
		border: 1px solid var(--border);
		border-radius: 0.25rem;
	}

	h3 {
		font-size: 1.125rem;
	}

	.decide {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0 2rem;
		align-items: start;
	}

	@media (max-width: 700px) {
		.decide {
			grid-template-columns: 1fr;
		}
	}

	.notes,
	.checklist {
		padding-inline-start: 1.25rem;
	}

	.checklist li {
		margin-block-end: 0.5rem;
	}

	.notes p {
		margin-block: 0.125rem;
	}

	.meta,
	.hint {
		color: var(--text-muted);
	}

	blockquote {
		margin: 0.25rem 0 0.75rem;
		padding-inline-start: 0.75rem;
		border-inline-start: 2px solid var(--border);
		overflow-wrap: anywhere;
		white-space: pre-wrap;
	}

	label {
		display: block;
		font-weight: 700;
		margin-block: 0.75rem 0.25rem;
	}

	textarea,
	select {
		display: block;
		inline-size: 100%;
		max-inline-size: 36rem;
		box-sizing: border-box;
		font: inherit;
		color: inherit;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 0.25rem;
		padding: 0.375rem 0.5rem;
	}

	button {
		font: inherit;
		color: inherit;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 0.25rem;
		padding: 0.375rem 0.75rem;
		cursor: pointer;
	}

	form > button {
		margin-block-start: 0.5rem;
	}

	.buttons {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
	}

	/* A failure is said in words and framed, never marked by colour alone. */
	.error {
		border-inline-start: 4px solid currentColor;
		padding-inline-start: 0.75rem;
	}
</style>
