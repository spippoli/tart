<script lang="ts">
	import type { ProposedOperation } from '#lib/contribution/proposed.ts';
	import { m } from '#lib/paraglide/messages.js';
	import type { OperationRow } from './rows';

	/**
	 * The operations of a round in words (Contribution and moderation spec, Submission page):
	 * what each one proposes and, beside it, what it replaces as the archive has it now. The
	 * values are the Submitter's text, so they carry the Content language.
	 */
	let {
		rows,
		lang,
		compare = true
	}: { rows: OperationRow[]; lang: string; compare?: boolean } = $props();

	const words: Record<ProposedOperation['type'], (inputs: { subject: string }) => string> = {
		create: m.contribution_operation_create,
		set: m.contribution_operation_set,
		add: m.contribution_operation_add,
		change: m.contribution_operation_change,
		remove: m.contribution_operation_remove
	};
</script>

<ol class="operations">
	{#each rows as row, index (index)}
		<li>
			<p>
				<strong>{words[row.operation.type]({ subject: row.operation.subject })}</strong>
				{#if row.fresh === true}
					<span class="mark">({m.moderation_rounds_new()})</span>
				{:else if row.fresh === false}
					<span class="mark">({m.moderation_rounds_unchanged()})</span>
				{/if}
			</p>
			{#if compare && row.operation.type === 'create'}
				<p class="hint">{m.moderation_compare_new()}</p>
			{/if}
			<dl>
				{#each row.operation.entries as [name, text] (name)}
					<div>
						<dt>{name}</dt>
						<dd {lang}>{text}</dd>
					</div>
				{/each}
			</dl>
			{#if compare && row.compared}
				<p class="current">
					<strong>{m.moderation_compare_current()}:</strong>
					{#if row.current !== null}<span {lang}>{row.current}</span
						>{:else}{m.moderation_compare_none()}{/if}
				</p>
			{/if}
		</li>
	{/each}
</ol>

<style>
	.operations {
		padding-inline-start: 1.25rem;
	}

	li {
		margin-block-end: 1rem;
	}

	p {
		margin-block: 0.125rem;
	}

	dl div {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem 0.75rem;
	}

	dt {
		font-weight: 700;
	}

	dt::after {
		content: ':';
	}

	dd {
		margin: 0;
		overflow-wrap: anywhere;
	}

	/* The current value is framed and labelled in words, never marked by colour alone. */
	.current {
		border-inline-start: 4px solid var(--border);
		padding-inline-start: 0.75rem;
		overflow-wrap: anywhere;
	}

	.hint,
	.mark {
		color: var(--text-muted);
	}
</style>
