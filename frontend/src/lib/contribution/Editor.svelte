<script lang="ts">
	import { onMount, tick, untrack, type Snippet } from 'svelte';
	import { signInHref } from '#lib/auth/next.ts';
	import { formatWait } from '#lib/i18n/format.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { localizeHref } from '#lib/paraglide/runtime.js';
	import * as api from './api';
	import { errorText } from './errors';
	import type { Session } from './session';
	import { stateWords } from './steps';

	/**
	 * The shell of every editor (Contribution and moderation spec, Submission form and
	 * Common rules): a stepper that can be walked in any order, never gating, with autosave
	 * to the server draft, validation on submit only, and an error summary that takes focus.
	 * What the steps hold is the editor's: its state is a `Session`, and `panel` draws the
	 * step that is open.
	 */
	let {
		editor,
		lastAutosave,
		panel
	}: {
		editor: Session;
		/** When the draft was last saved by its Submitter, if it ever was. */
		lastAutosave: string | null;
		/** The open step, with the function that submits the Submission (for the Review step). */
		panel: Snippet<[string, () => void]>;
	} = $props();

	// The editor is made once, from what the page loaded; a draft does not change under it.
	// svelte-ignore state_referenced_locally
	const config = editor.config;
	// svelte-ignore state_referenced_locally
	if (lastAutosave) editor.save = { kind: 'saved', at: new Date(lastAutosave) };
	const id = config.submissionId;
	const format = { locale: config.locale, timeZone: config.timeZone };

	// ---- steps ----

	let heading = $state<HTMLElement>();
	let summary = $state<HTMLElement>();

	async function go(step: string) {
		editor.step = step;
		await tick();
		heading?.focus();
	}

	const position = $derived(editor.steps.indexOf(editor.step));

	async function follow(event: MouseEvent, error: { id: string; step: string }) {
		event.preventDefault();
		editor.step = error.step;
		await tick();
		const target = document.getElementById(error.id);
		(target ?? heading)?.focus();
	}

	// ---- autosave ----

	const serialized = $derived(JSON.stringify(editor.workingCopy));
	let saved = untrack(() => JSON.stringify(editor.workingCopy));
	let timer: ReturnType<typeof setTimeout> | undefined;
	let queue: Promise<unknown> = Promise.resolve();

	function waitWords(failure: api.Failure): string {
		return failure.retryAfter !== undefined ? formatWait(failure.retryAfter, format) : '';
	}

	function flush(): Promise<unknown> {
		queue = queue.then(async () => {
			const current = JSON.stringify(untrack(() => editor.workingCopy));
			if (current === saved) return;
			editor.save = { kind: 'saving' };
			const out = await api.autosave(id, JSON.parse(current));
			if (out.ok) {
				saved = current;
				editor.save = { kind: 'saved', at: new Date(out.value.last_autosave_at) };
			} else {
				editor.save = { kind: 'failed', failure: out.failure };
			}
		});
		return queue;
	}

	$effect(() => {
		if (serialized === saved) return;
		clearTimeout(timer);
		timer = setTimeout(() => void flush(), 1000);
		return () => clearTimeout(timer);
	});

	const saveStatus = $derived.by(() => {
		const status = editor.save;
		switch (status.kind) {
			case 'saving':
				return m.editor_autosave_saving();
			case 'saved':
				return m.editor_autosave_saved({
					time: new Intl.DateTimeFormat(config.locale, {
						hour: '2-digit',
						minute: '2-digit',
						timeZone: config.timeZone
					}).format(status.at)
				});
			case 'failed':
				return m.editor_autosave_failed({
					reason: errorText(status.failure.code, { wait: waitWords(status.failure) })
				});
			default:
				return m.editor_autosave_idle();
		}
	});

	onMount(() => {
		const warn = (event: BeforeUnloadEvent) => {
			if (JSON.stringify(editor.workingCopy) !== saved) event.preventDefault();
		};
		window.addEventListener('beforeunload', warn);
		return () => window.removeEventListener('beforeunload', warn);
	});

	/**
	 * Leaves the editor for a page of this app. A full page load, not a client navigation:
	 * the next page then reads the Submissions afresh, and nothing of the editor stays.
	 */
	function leave(path: string) {
		window.location.assign(localizeHref(path));
	}

	// ---- submit ----

	async function showSummary() {
		await tick();
		summary?.focus();
	}

	async function submit() {
		editor.attempted = true;
		editor.refused = [];
		const errors = editor.live;
		editor.submitted = errors;
		if (errors.length > 0) {
			editor.announce(m.editor_summary_announcement({ count: errors.length }));
			await showSummary();
			return;
		}
		editor.submitting = true;
		const out = await api.submit(id, editor.workingCopy, editor.note, editor.termsAccepted);
		editor.submitting = false;
		if (out.ok) {
			saved = JSON.stringify(editor.workingCopy);
			leave(`/contributions/${id}`);
			return;
		}
		if (out.failure.status === 401) {
			window.location.href = signInHref(window.location);
			return;
		}
		const refusal = editor.serverError(out.failure.code);
		refusal.params = { wait: waitWords(out.failure) };
		editor.refused = [refusal];
		editor.announce(m.editor_summary_announcement({ count: 1 }));
		await showSummary();
	}

	// ---- leaving ----

	let confirmingDelete = $state(false);
	let leaveError = $state<string | null>(null);

	async function exitLater() {
		clearTimeout(timer);
		await flush();
		if (editor.save.kind === 'failed') return;
		saved = JSON.stringify(editor.workingCopy);
		leave('/account/contributions');
	}

	async function deleteDraft() {
		const out = await api.deleteDraft(id);
		if (!out.ok) {
			leaveError = errorText(out.failure.code);
			return;
		}
		saved = JSON.stringify(editor.workingCopy);
		leave('/account/contributions');
	}
</script>

<div class="editor">
	<p class="status" role="status">{saveStatus}</p>
	<p class="visually-hidden" role="status">{editor.announcement}</p>

	{#if editor.resumed}
		<aside class="resumed" aria-label={m.editor_resumed_label()}>
			<p>{m.editor_resumed({ step: editor.stepName(editor.resumed) })}</p>
			<button type="button" onclick={() => (editor.resumed = null)}>{m.editor_dismiss()}</button>
		</aside>
	{/if}

	{#if editor.shown.length > 0}
		<section
			bind:this={summary}
			id="editor-summary"
			class="summary"
			role="alert"
			tabindex="-1"
			aria-labelledby="editor-summary-title"
		>
			<h2 id="editor-summary-title">{m.editor_summary_title({ count: editor.shown.length })}</h2>
			<ul>
				{#each editor.shown as error (error.id + error.code)}
					<li>
						<a href="#{error.id}" onclick={(event) => follow(event, error)}>
							<span class="where">{editor.stepName(error.step)}:</span>
							{errorText(error.code, error.params)}
						</a>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	<nav aria-label={m.editor_steps()}>
		<ol class="steps">
			{#each editor.steps as step, index (step)}
				<li>
					<button
						type="button"
						class="step-button"
						aria-current={editor.step === step ? 'step' : undefined}
						onclick={() => go(step)}
					>
						<span class="number">{index + 1}.</span>
						<span class="name">{editor.stepName(step)}</span>
						<span class="state">{stateWords[editor.states[step]]()}</span>
					</button>
				</li>
			{/each}
		</ol>
	</nav>

	<section class="panel" aria-labelledby="editor-step-heading">
		<h2 id="editor-step-heading" tabindex="-1" bind:this={heading}>
			{m.editor_step_heading({
				number: position + 1,
				count: editor.steps.length,
				name: editor.stepName(editor.step)
			})}
		</h2>
		{@render panel(editor.step, submit)}
	</section>

	<div class="movement">
		<button type="button" disabled={position === 0} onclick={() => go(editor.steps[position - 1])}>
			{m.editor_previous()}
		</button>
		<button
			type="button"
			disabled={position === editor.steps.length - 1}
			onclick={() => go(editor.steps[position + 1])}
		>
			{m.editor_next()}
		</button>
	</div>

	<div class="leave">
		<button type="button" onclick={exitLater}>{m.editor_exit()}</button>
		{#if confirmingDelete}
			<span class="confirm" role="group" aria-label={m.editor_delete_confirm_label()}>
				{m.editor_delete_confirm()}
				<button type="button" onclick={deleteDraft}>{m.editor_delete_yes()}</button>
				<button type="button" onclick={() => (confirmingDelete = false)}
					>{m.editor_delete_no()}</button
				>
			</span>
		{:else}
			<button type="button" onclick={() => (confirmingDelete = true)}>{m.editor_delete()}</button>
		{/if}
		{#if leaveError}<p class="error">{leaveError}</p>{/if}
	</div>
</div>

<style>
	.editor {
		display: grid;
		gap: 1.25rem;
	}

	.editor > p,
	.resumed p {
		margin: 0;
	}

	.status {
		color: var(--text-muted);
	}

	.resumed {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		align-items: center;
		border: 1px solid var(--border);
		padding: 0.5rem 0.75rem;
	}

	.summary {
		border: 3px solid var(--text);
		padding: 0.75rem 1rem;
	}

	.summary h2 {
		margin: 0 0 0.5rem;
		font-size: 1.1rem;
	}

	.summary ul {
		margin: 0;
		padding-inline-start: 1.25rem;
		display: grid;
		gap: 0.35rem;
	}

	.where {
		font-weight: 600;
	}

	.steps {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.step-button {
		display: grid;
		gap: 0.1rem;
		justify-items: start;
		text-align: start;
		min-inline-size: 7.5rem;
	}

	.step-button[aria-current='step'] {
		border: 3px solid var(--text);
		font-weight: 700;
	}

	.state {
		font-size: 0.85rem;
		color: var(--text-muted);
	}

	.panel h2 {
		margin-block-start: 0;
	}

	.movement,
	.leave {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		align-items: center;
	}

	.leave {
		border-block-start: 1px solid var(--border);
		padding-block-start: 1rem;
	}

	.confirm {
		display: inline-flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		align-items: center;
	}

	.error {
		margin: 0;
	}

	button {
		min-block-size: 2.75rem;
		padding: 0.25rem 0.75rem;
		background: var(--background);
		color: var(--text);
		border: 1px solid var(--border);
		cursor: pointer;
	}

	button:disabled {
		cursor: default;
		opacity: 0.6;
	}
</style>
