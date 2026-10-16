<script lang="ts">
	import { formatDate } from '#lib/i18n/format.ts';
	import { kindText, labelText, STATUSES, statusText } from '#lib/contribution/words.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { localizeHref } from '#lib/paraglide/runtime.js';
	import PageTitle from '#lib/shell/PageTitle.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const formatContext = $derived({ locale: data.locale, timeZone: data.timeZone });

	/** A draft opens in the editor; every other Submission on its page. */
	function href(submission: (typeof data.submissions)[number]): string {
		const base = localizeHref(`/contributions/${submission.id}`);
		return submission.status === 'draft'
			? localizeHref(`/contributions/${submission.id}/edit`)
			: base;
	}
</script>

<PageTitle title={m.my_contributions_title()} />

<h1>{m.my_contributions_title()}</h1>
<p class="intro">{m.my_contributions_intro()}</p>

<form method="get" class="filter">
	<label for="status">{m.my_contributions_filter_label()}</label>
	<select id="status" name="status">
		<option value="" selected={data.status === null}>{m.my_contributions_filter_all()}</option>
		{#each STATUSES as status (status)}
			<option value={status} selected={data.status === status}>{statusText(status)}</option>
		{/each}
	</select>
	<button type="submit">{m.my_contributions_filter_submit()}</button>
</form>

<p role="status">
	{m.my_contributions_count({ count: data.submissions.length })}
</p>

{#if data.submissions.length === 0}
	<p>{data.status === null ? m.my_contributions_empty() : m.my_contributions_empty_filtered()}</p>
	<p><a href={localizeHref('/contribute')}>{m.my_contributions_start_link()}</a></p>
{:else}
	<!-- A table wider than the screen scrolls, so keyboard users must be able to focus it. -->
	<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
	<div class="scroll" role="region" aria-label={m.my_contributions_title()} tabindex="0">
		<table>
			<caption class="visually-hidden">{m.my_contributions_caption()}</caption>
			<thead>
				<tr>
					<th scope="col">{m.my_contributions_column_contribution()}</th>
					<th scope="col">{m.my_contributions_column_status()}</th>
					<th scope="col">{m.my_contributions_column_date()}</th>
				</tr>
			</thead>
			<tbody>
				{#each data.submissions as submission (submission.id)}
					<tr>
						<th scope="row">
							<a href={href(submission)}
								>{m.contribution_heading({
									kind: kindText(submission.intent, submission.target_kind),
									number: submission.id
								})}</a
							>
							{#if submission.labels.length > 0}
								<ul class="labels">
									{#each submission.labels as label (label)}
										<li>{labelText(label)}</li>
									{/each}
								</ul>
							{/if}
						</th>
						<td>
							{statusText(submission.status)}
							{#if submission.expires_at && submission.status === 'changes_requested'}
								<br />
								<span class="hint"
									>{m.contribution_expires({
										date: formatDate(submission.expires_at, formatContext)
									})}</span
								>
							{/if}
						</td>
						<td>{formatDate(submission.updated_at, formatContext)}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/if}

<style>
	.intro {
		max-inline-size: 40rem;
	}

	.filter {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem;
		margin-block-end: 1rem;
	}

	label {
		font-weight: 700;
	}

	select,
	button {
		font: inherit;
		color: inherit;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 0.25rem;
		padding: 0.375rem 0.5rem;
	}

	button {
		cursor: pointer;
	}

	.hint {
		color: var(--text-muted);
	}

	.labels {
		margin: 0.25rem 0 0;
		padding: 0;
		list-style: none;
		font-weight: 400;
		color: var(--text-muted);
	}

	.scroll {
		overflow-x: auto;
	}

	table {
		border-collapse: collapse;
		inline-size: 100%;
	}

	th,
	td {
		text-align: start;
		padding: 0.5rem 0.75rem;
		border-block-end: 1px solid var(--border);
		vertical-align: top;
	}

	.visually-hidden {
		position: absolute;
		inline-size: 1px;
		block-size: 1px;
		overflow: hidden;
		clip-path: inset(50%);
		white-space: nowrap;
	}
</style>
