<script lang="ts">
	import { page } from '$app/state';
	import { signInHref } from '#lib/auth/next.ts';
	import { formatDate, formatDateTime } from '#lib/i18n/format.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { localizeHref } from '#lib/paraglide/runtime.js';
	import ChangeValue from './ChangeValue.svelte';
	import { archiveContext } from './context.svelte';
	import ModeratorNotice from './ModeratorNotice.svelte';
	import RecordAnchor from './RecordAnchor.svelte';
	import {
		linkText,
		recordHref,
		reportHref,
		revisionsHref,
		type Kind,
		type RevisionsView
	} from './records';
	import PageTitle from '../shell/PageTitle.svelte';

	/**
	 * A record's `/revisions` subpage (archive-records spec, criteria 21 and 26): its
	 * Revisions, most recent first, each at a stable anchor with the Submitter's display
	 * name (no profile link, never the approving Moderator), its dates, a change list
	 * with previous and new values, and its own Report link. A redacted value shows the
	 * placeholder wherever it appears, including as a later previous value.
	 */
	let { view, kind }: { view: RevisionsView; kind: Kind } = $props();
	const context = archiveContext();
	const name = $derived(linkText(view.record, context.surfaceType, context.locale));
	const fieldLabel = (field: string | null | undefined) => {
		const message = (m as unknown as Record<string, () => string>)[`archive_field_${field}`];
		return message ? message() : (field ?? '');
	};
	const unmergeHref = $derived(
		page.data.user
			? `${localizeHref('/contribute/unmerge')}?kind=${kind}&source=${view.record.id}`
			: signInHref(page.url)
	);
	const operations = {
		add: m.archive_change_add,
		remove: m.archive_change_remove,
		change: m.archive_change_change
	};
</script>

<PageTitle title={m.archive_revisions_title({ name })} />

<article>
	<ModeratorNotice withdrawnAt={view.withdrawn_at} />
	<h1>{m.archive_revisions_title({ name })}</h1>
	<p>{m.archive_revisions_intro()}</p>
	{#if view.merged_into}
		<p class="merged">{m.archive_merged_into()} <RecordAnchor link={view.merged_into} /></p>
		<p>
			<a href={unmergeHref}>
				{kind === 'documentation_item'
					? m.merge_action_unmerge_retirement()
					: m.merge_action_unmerge()}
			</a>
		</p>
	{:else}
		<p><a href={recordHref(kind, view.record.path)}>{m.archive_revisions_back()}</a></p>
	{/if}

	<ol class="revisions">
		{#each view.revisions as revision, index (revision.id)}
			{@const first = index === view.revisions.length - 1}
			<li id="revision-{revision.id}">
				<h2>
					{m.archive_revision_heading({
						date: formatDateTime(revision.approved_at, context.dates)
					})}
				</h2>
				<p class="meta">
					{m.archive_revision_by({
						name: revision.submitter ?? m.archive_revision_former_contributor()
					})}
					· {m.archive_revision_submitted({
						date: formatDate(revision.submitted_at, context.dates)
					})}
					· {m.archive_revision_approved({ date: formatDate(revision.approved_at, context.dates) })}
				</p>
				<ul class="changes">
					{#each revision.changes as change, position (position)}
						{@const field = change.field ?? change.collection ?? ''}
						{#if change.op === 'merge' || change.op === 'unmerge'}
							<li>
								<span class="what"
									>{change.op === 'merge'
										? m.merge_revision_merge()
										: m.merge_revision_unmerge()}</span
								>
								{#if change.record}
									<a href={revisionsHref(change.record.kind, change.record.path)}
										>{linkText(change.record, context.surfaceType, context.locale)}</a
									>
								{:else}
									{m.merge_revision_record()}
								{/if}
							</li>
						{:else}
							<li>
								<span class="what"
									>{change.op === 'set'
										? first
											? fieldLabel(field)
											: m.archive_change_set({ field: fieldLabel(field) })
										: operations[change.op]({ field: fieldLabel(field) })}</span
								>{#if change.redacted && change.redacted_at}
									<span class="redacted"
										>({m.archive_redacted_marker({
											date: formatDate(change.redacted_at, context.dates)
										})})</span
									>{/if}:
								{#if change.redacted && !change.redacted_at}
									<span class="redacted">{m.archive_content_redacted()}</span>
								{:else if change.op === 'set' && !first}
									<dl>
										<dt>{m.archive_change_before()}</dt>
										<dd>
											{#if change.old_redacted && !change.redacted_at && change.old === null}
												<span class="redacted">{m.archive_content_redacted()}</span>
											{:else}
												<ChangeValue {field} value={change.old} records={view.records} />
											{/if}
										</dd>
										<dt>{m.archive_change_after()}</dt>
										<dd><ChangeValue {field} value={change.new} records={view.records} /></dd>
									</dl>
								{:else if change.op === 'set'}
									<ChangeValue {field} value={change.new} records={view.records} />
								{:else if change.op === 'change'}
									<dl>
										<dt>{m.archive_change_before()}</dt>
										<dd>
											{#if change.old_redacted && change.old === null}
												<span class="redacted">{m.archive_content_redacted()}</span>
											{:else}
												<ChangeValue {field} value={change.old} records={view.records} />
											{/if}
										</dd>
										<dt>{m.archive_change_after()}</dt>
										<dd><ChangeValue {field} value={change.new} records={view.records} /></dd>
									</dl>
								{:else}
									<ChangeValue {field} value={change.item} records={view.records} />
								{/if}
							</li>
						{/if}
					{/each}
				</ul>
				<p>
					<a href={reportHref(context.locale, kind, view.record.id, revision.id)}
						>{m.archive_revision_report()}</a
					>
				</p>
			</li>
		{/each}
	</ol>
</article>

<style>
	.revisions {
		list-style: none;
		padding: 0;
		display: grid;
		gap: 1.5rem;
	}
	.revisions > li {
		border-block-start: 1px solid var(--border);
		padding-block-start: 0.5rem;
	}
	.meta {
		color: var(--text-muted);
	}
	.changes {
		display: grid;
		gap: 0.4rem;
	}
	.what {
		font-weight: 600;
	}
	.redacted {
		font-style: italic;
		color: var(--text-muted);
	}
	dl {
		display: grid;
		grid-template-columns: max-content 1fr;
		gap: 0 1rem;
		margin: 0.25rem 0;
	}
	dt {
		color: var(--text-muted);
	}
	dd {
		margin: 0;
	}
</style>
