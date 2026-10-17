<script lang="ts">
	import { enhance } from '$app/forms';
	import {
		errorText,
		eventText,
		kindText,
		labelText,
		statusText,
		type SubmissionKind
	} from '#lib/contribution/words.ts';
	import { formatDate, formatDateTime } from '#lib/i18n/format.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { localizeHref } from '#lib/paraglide/runtime.js';
	import GeometryComparison from '#lib/moderation/GeometryComparison.svelte';
	import ImageComparison from '#lib/moderation/ImageComparison.svelte';
	import ModeratorPanel from '#lib/moderation/ModeratorPanel.svelte';
	import OperationList from '#lib/moderation/OperationList.svelte';
	import { operationRows } from '#lib/moderation/rows.ts';
	import { diffRounds } from '#lib/moderation/rounds.ts';
	import PageTitle from '#lib/shell/PageTitle.svelte';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();

	const formatContext = $derived({ locale: data.locale, timeZone: data.timeZone });
	const submission = $derived(data.submission);
	const heading = $derived(
		m.contribution_heading({
			kind: kindText(submission.intent, submission.target_kind),
			number: submission.id
		})
	);
	const status = $derived(submission.status);
	const open = $derived(status === 'submitted' || status === 'changes_requested');

	const recordRoutes: Record<SubmissionKind, string | null> = {
		artwork: '/artworks',
		location: '/locations',
		site: '/sites',
		area: '/areas',
		series: '/series',
		artist: '/artists',
		source: '/sources',
		documentation_item: '/documents'
	};
	const targetHref = $derived(
		submission.target_id !== null && recordRoutes[submission.target_kind]
			? localizeHref(`${recordRoutes[submission.target_kind]}/${submission.target_id}`)
			: null
	);

	const editHref = $derived(localizeHref(`/contributions/${submission.id}/edit`));
	const related = (id: number) => localizeHref(`/contributions/${id}`);

	function reasonLabel(key: string | null): string | null {
		if (key === null) return null;
		const entry = data.decisionReasons.find((each) => each.key === key);
		return entry ? (entry.label[data.locale] ?? entry.label[data.contentLanguage] ?? key) : key;
	}

	/** The last Decision message: the message of the latest rejection or request for changes. */
	const decision = $derived(
		[...submission.log]
			.reverse()
			.find((entry) => entry.event === 'rejected' || entry.event === 'changes_requested')
	);

	function actorText(actor: (typeof submission.log)[number]['actor']): string {
		if (actor.role === 'system') return m.contribution_actor_system();
		if (actor.role === 'submitter') {
			return data.own ? m.contribution_actor_you() : m.contribution_actor_submitter();
		}
		return actor.user
			? m.contribution_actor_named_moderator({
					name: actor.user.display_name,
					number: actor.user.number
				})
			: m.contribution_actor_moderator();
	}

	const rows = $derived(operationRows(submission.last_round, data.comparison?.operations ?? []));
	const rounds = $derived(data.comparison?.rounds ?? []);
	const previousRound = $derived(rounds.length > 1 ? rounds[rounds.length - 2] : null);
	const roundDiff = $derived(
		previousRound ? diffRounds(previousRound.snapshot, submission.last_round) : null
	);
	const diffRows = $derived(
		roundDiff
			? operationRows(
					submission.last_round,
					[],
					roundDiff.current.map((each) => each.fresh)
				)
			: []
	);
	const removedRows = $derived(
		roundDiff ? operationRows({ operations: roundDiff.removed }, []) : []
	);
	const writtenAgainst = $derived(submission.base_revisions[0] ?? null);

	const outcome = $derived(
		form && 'section' in form ? (form as { section?: string; code?: string; done?: string }) : null
	);

	// The notes and the decision say their own failures, next to their forms.
	const failure = $derived(
		form && 'code' in form && !('section' in form)
			? errorText(
					String(form.code),
					'retryAfter' in form ? Number(form.retryAfter) : undefined,
					formatContext
				)
			: undefined
	);
</script>

<PageTitle title={heading} />

<h1>{heading}</h1>

<dl class="facts">
	<div>
		<dt>{m.contribution_status_label()}</dt>
		<dd><strong>{statusText(status)}</strong></dd>
	</div>
	{#if targetHref}
		<div>
			<dt>{m.contribution_target_label()}</dt>
			<dd>
				<a href={targetHref}>{m.contribution_target_link({ number: submission.target_id ?? 0 })}</a>
			</dd>
		</div>
	{/if}
	{#if data.moderator && !data.own}
		<div>
			<dt>{m.moderation_submitter_label()}</dt>
			<dd>
				{submission.submitter.display_name === ''
					? m.moderation_queue_submitter_deleted({ number: submission.submitter.number })
					: m.moderation_queue_submitter({
							name: submission.submitter.display_name,
							number: submission.submitter.number
						})}
			</dd>
		</div>
	{/if}
	{#if submission.labels.length > 0}
		<div>
			<dt>{m.contribution_labels_label()}</dt>
			<dd>{submission.labels.map(labelText).join(', ')}</dd>
		</div>
	{/if}
	<div>
		<dt>{m.contribution_started_label()}</dt>
		<dd>{formatDate(submission.created_at, formatContext)}</dd>
	</div>
	{#if submission.first_submitted_at}
		<div>
			<dt>{m.contribution_first_submitted_label()}</dt>
			<dd>{formatDate(submission.first_submitted_at, formatContext)}</dd>
		</div>
	{/if}
	{#if submission.rounds > 0}
		<div>
			<dt>{m.contribution_rounds_label()}</dt>
			<dd>{submission.rounds}</dd>
		</div>
	{/if}
</dl>

{#if status === 'draft'}
	<p class="notice">{m.contribution_notice_draft()}</p>
{/if}
{#if status === 'submitted'}
	<p class="notice">{m.contribution_notice_submitted()}</p>
{/if}
{#if status === 'changes_requested'}
	<p class="notice">
		{m.contribution_notice_changes_requested()}
		{#if submission.expires_at}
			{m.contribution_expires({ date: formatDate(submission.expires_at, formatContext) })}
		{/if}
	</p>
{/if}
{#if submission.outdated.length > 0}
	<p class="notice">{m.contribution_notice_outdated()}</p>
{/if}
{#if submission.working_copy_discarded}
	<p class="notice">{m.contribution_notice_working_copy_discarded()}</p>
{/if}
{#if submission.stub}
	<p class="notice">{m.contribution_notice_stub()}</p>
{/if}

<p role="status">
	{#if form && 'retracted' in form}{m.contribution_retracted_done()}{/if}
</p>
{#if failure}
	<p class="error" role="alert"><strong>{failure}</strong></p>
{/if}

{#if data.own}
	<section aria-labelledby="actions-heading">
		<h2 id="actions-heading">{m.contribution_actions_heading()}</h2>
		<div class="actions">
			{#if status === 'draft'}
				<a class="button" href={editHref}>{m.contribution_action_continue()}</a>
			{:else if status === 'submitted'}
				<a class="button" href={editHref}>{m.contribution_action_revise()}</a>
			{:else if status === 'changes_requested'}
				<a class="button" href={editHref}>{m.contribution_action_resubmit()}</a>
			{/if}

			{#if status === 'rejected' || status === 'retracted'}
				<form method="post" action="?/startAgain" use:enhance>
					<button type="submit">{m.contribution_action_start_again()}</button>
				</form>
			{/if}

			{#if open}
				<details>
					<summary>{m.contribution_action_retract()}</summary>
					<p>{m.contribution_retract_confirm()}</p>
					<form method="post" action="?/retract" use:enhance>
						<button type="submit">{m.contribution_retract_submit()}</button>
					</form>
				</details>
			{/if}

			{#if status === 'draft'}
				<details>
					<summary>{m.contribution_action_delete()}</summary>
					<p>{m.contribution_delete_confirm()}</p>
					<form method="post" action="?/delete" use:enhance>
						<button type="submit">{m.contribution_delete_submit()}</button>
					</form>
				</details>
			{/if}
		</div>
	</section>
{/if}

{#if data.moderator}
	<ModeratorPanel
		{submission}
		reasons={data.decisionReasons}
		context={formatContext}
		contentLanguage={data.contentLanguage}
		own={data.own}
		{outcome}
	/>
{/if}

{#if decision && (decision.message || decision.reason)}
	<section aria-labelledby="decision-heading">
		<h2 id="decision-heading">{m.contribution_decision_heading()}</h2>
		<p>
			{#if decision.reason}<strong>{reasonLabel(decision.reason)}</strong>{/if}
		</p>
		{#if decision.message}
			<blockquote lang={data.contentLanguage}>{decision.message}</blockquote>
		{/if}
	</section>
{/if}

{#if !submission.stub && submission.last_round !== null}
	<section aria-labelledby="proposed-heading">
		<h2 id="proposed-heading">{m.moderation_compare_heading()}</h2>
		<p>{m.moderation_compare_intro({ round: submission.rounds })}</p>
		{#if writtenAgainst !== null && data.comparison?.current_revision && data.comparison.current_revision !== writtenAgainst}
			<p>
				{m.moderation_compare_revision({
					base: writtenAgainst,
					current: data.comparison.current_revision
				})}
			</p>
		{/if}
		{#if rows.length === 0}
			<p>{m.contribution_proposed_empty()}</p>
		{:else}
			<OperationList {rows} lang={data.contentLanguage} />
		{/if}
	</section>

	{#if data.comparison && data.comparison.images.length > 0}
		<section aria-labelledby="images-heading">
			<h2 id="images-heading">{m.moderation_images_heading()}</h2>
			{#each data.comparison.images as images, index (index)}
				<ImageComparison
					comparison={images}
					context={formatContext}
					contentLanguage={data.contentLanguage}
				/>
			{/each}
		</section>
	{/if}

	{#if data.comparison && data.comparison.geometries.length > 0}
		<section aria-labelledby="geometry-heading">
			<h2 id="geometry-heading">{m.moderation_geometry_heading()}</h2>
			{#each data.comparison.geometries as geometry, index (index)}
				<h3>
					{#if geometry.record_kind === 'area'}
						{geometry.target_id === null
							? m.moderation_geometry_new_area()
							: m.moderation_geometry_changed_area({ id: geometry.target_id })}
					{:else}
						{geometry.target_id === null
							? m.moderation_geometry_new_location()
							: m.moderation_geometry_moved_location({ id: geometry.target_id })}
					{/if}
				</h3>
				<GeometryComparison comparison={geometry} locale={data.locale} />
			{/each}
		</section>
	{/if}

	{#if previousRound}
		<section aria-labelledby="rounds-heading">
			<h2 id="rounds-heading">{m.moderation_rounds_heading()}</h2>
			<p>
				{m.moderation_rounds_intro({
					round: submission.rounds,
					previous: previousRound.number
				})}
			</p>
			<OperationList rows={diffRows} lang={data.contentLanguage} compare={false} />
			{#if removedRows.length > 0}
				<h3>{m.moderation_rounds_removed()}</h3>
				<OperationList rows={removedRows} lang={data.contentLanguage} compare={false} />
			{/if}
			{#each rounds.slice(0, -1) as round (round.number)}
				<details>
					<summary
						>{m.moderation_rounds_summary({
							number: round.number,
							date: formatDate(round.submitted_at, formatContext)
						})}</summary
					>
					<OperationList
						rows={operationRows(round.snapshot, [])}
						lang={data.contentLanguage}
						compare={false}
					/>
				</details>
			{/each}
		</section>
	{/if}
{/if}

<section aria-labelledby="log-heading">
	<h2 id="log-heading">{m.contribution_log_heading()}</h2>
	{#if submission.log.length === 0}
		<p>{m.contribution_log_empty()}</p>
	{:else}
		<ol class="log">
			{#each submission.log as entry, index (index)}
				<li>
					<p>
						<strong>{eventText(entry.event, entry.round, entry.related_submission)}</strong>
						{#if entry.related_submission !== null}
							(<a href={related(entry.related_submission)}
								>{m.contribution_log_related({ number: entry.related_submission })}</a
							>)
						{/if}
					</p>
					<p class="meta">
						{m.contribution_log_by({ actor: actorText(entry.actor) })} ·
						<time datetime={entry.at}>{formatDateTime(entry.at, formatContext)}</time>
					</p>
					{#if entry.reason}
						<p>{m.contribution_log_reason({ reason: reasonLabel(entry.reason) ?? '' })}</p>
					{/if}
					{#if entry.message}
						<blockquote lang={data.contentLanguage}>{entry.message}</blockquote>
					{/if}
				</li>
			{/each}
		</ol>
	{/if}
</section>

<p><a href={localizeHref('/account/contributions')}>{m.contribution_back()}</a></p>

<style>
	section {
		max-inline-size: 50rem;
		margin-block-end: 2rem;
	}

	.facts {
		display: grid;
		gap: 0.25rem;
		margin: 0 0 1.5rem;
	}

	.facts div {
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

	/* A notice is said in words and framed, never marked by colour alone. */
	.notice,
	.error {
		border-inline-start: 4px solid currentColor;
		padding-inline-start: 0.75rem;
		max-inline-size: 50rem;
	}

	.actions {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-start;
		gap: 0.75rem;
	}

	.button,
	button,
	summary {
		font: inherit;
		color: inherit;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 0.25rem;
		padding: 0.375rem 0.75rem;
		cursor: pointer;
		text-decoration: none;
		display: inline-block;
	}

	details {
		max-inline-size: 30rem;
	}

	summary {
		list-style-position: inside;
	}

	blockquote {
		margin: 0.5rem 0;
		padding-inline-start: 0.75rem;
		border-inline-start: 2px solid var(--border);
		overflow-wrap: anywhere;
	}

	.log {
		padding-inline-start: 1.25rem;
	}

	.log li {
		margin-block-end: 1rem;
	}

	.log p {
		margin-block: 0.125rem;
	}

	.meta {
		color: var(--text-muted);
	}
</style>
