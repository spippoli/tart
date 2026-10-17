<script lang="ts">
	import { kindText, labelText } from '#lib/contribution/words.ts';
	import { formatDate } from '#lib/i18n/format.ts';
	import { KINDS, kindName, LABELS, SORTS, sortText } from '#lib/moderation/words.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { localizeHref } from '#lib/paraglide/runtime.js';
	import PageTitle from '#lib/shell/PageTitle.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const formatContext = $derived({ locale: data.locale, timeZone: data.timeZone });
	const filtered = $derived(
		data.filters.label !== '' ||
			data.filters.kind !== '' ||
			data.filters.submitter !== '' ||
			data.filters.area !== '' ||
			data.filters.outdated !== ''
	);

	const submission = (id: number) => localizeHref(`/contributions/${id}`);

	function submitterText(person: { number: number; display_name: string }): string {
		return person.display_name === ''
			? m.moderation_queue_submitter_deleted({ number: person.number })
			: m.moderation_queue_submitter({ name: person.display_name, number: person.number });
	}
</script>

<PageTitle title={m.moderation_queue_title()} />

<h1>{m.moderation_queue_title()}</h1>
<p class="intro">{m.moderation_queue_intro()}</p>

<!-- The fields start again from the query when it changes, so that clearing the filters clears them. -->
{#key JSON.stringify(data.filters)}
	<form method="get" class="filters" aria-labelledby="filters-heading">
		<h2 id="filters-heading">{m.moderation_queue_filter_heading()}</h2>
		<div class="fields">
			<div>
				<label for="sort">{m.moderation_queue_sort_label()}</label>
				<select id="sort" name="sort">
					{#each SORTS as sort (sort)}
						<option value={sort} selected={data.filters.sort === sort}>{sortText(sort)}</option>
					{/each}
				</select>
			</div>
			<div>
				<label for="label">{m.moderation_queue_filter_label()}</label>
				<select id="label" name="label">
					<option value="">{m.moderation_queue_any()}</option>
					{#each LABELS as label (label)}
						<option value={label} selected={data.filters.label === label}>{labelText(label)}</option
						>
					{/each}
				</select>
			</div>
			<div>
				<label for="kind">{m.moderation_queue_filter_kind()}</label>
				<select id="kind" name="kind">
					<option value="">{m.moderation_queue_any()}</option>
					{#each KINDS as kind (kind)}
						<option value={kind} selected={data.filters.kind === kind}>{kindName(kind)}</option>
					{/each}
				</select>
			</div>
			<div>
				<label for="submitter">{m.moderation_queue_filter_submitter()}</label>
				<input
					id="submitter"
					name="submitter"
					type="text"
					inputmode="numeric"
					pattern="[0-9]*"
					autocomplete="off"
					value={data.filters.submitter}
				/>
			</div>
			<div>
				<label for="area">{m.moderation_queue_filter_area()}</label>
				<select id="area" name="area">
					<option value="">{m.moderation_queue_any()}</option>
					{#each data.areas as area (area.id)}
						<option
							value={area.id}
							selected={data.filters.area === String(area.id)}
							lang={data.contentLanguage}>{area.name}</option
						>
					{/each}
				</select>
			</div>
			<div>
				<label for="outdated">{m.moderation_queue_filter_outdated()}</label>
				<select id="outdated" name="outdated">
					<option value="">{m.moderation_queue_any()}</option>
					<option value="yes" selected={data.filters.outdated === 'yes'}
						>{m.moderation_queue_outdated_yes()}</option
					>
					<option value="no" selected={data.filters.outdated === 'no'}
						>{m.moderation_queue_outdated_no()}</option
					>
				</select>
			</div>
		</div>
		<p class="buttons">
			<button type="submit">{m.moderation_queue_apply()}</button>
			{#if filtered || data.filters.sort !== SORTS[0]}
				<a href={localizeHref('/moderation')}>{m.moderation_queue_reset()}</a>
			{/if}
		</p>
	</form>
{/key}

<p role="status">{m.moderation_queue_count({ count: data.items.length })}</p>

{#if data.items.length === 0}
	<p>{filtered ? m.moderation_queue_empty_filtered() : m.moderation_queue_empty()}</p>
{:else}
	<!-- A table wider than the screen scrolls, so keyboard users must be able to focus it. -->
	<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
	<div class="scroll" role="region" aria-label={m.moderation_queue_caption()} tabindex="0">
		<table>
			<caption class="visually-hidden">{m.moderation_queue_caption()}</caption>
			<thead>
				<tr>
					<th scope="col">{m.moderation_queue_column_submission()}</th>
					<th scope="col">{m.moderation_queue_column_submitter()}</th>
					<th scope="col">{m.moderation_queue_column_submitted()}</th>
					<th scope="col">{m.moderation_queue_column_flags()}</th>
				</tr>
			</thead>
			<tbody>
				{#each data.items as item (item.id)}
					<tr>
						<th scope="row">
							<a href={submission(item.id)}
								>{m.contribution_heading({
									kind: kindText(item.intent, item.target_kind),
									number: item.id
								})}</a
							>
							{#if item.labels.length > 0}
								<ul class="plain">
									{#each item.labels as label (label)}
										<li>{labelText(label)}</li>
									{/each}
								</ul>
							{/if}
						</th>
						<td>
							{submitterText(item.submitter)}
							{#if item.own}<br /><span class="hint">{m.moderation_queue_own()}</span>{/if}
						</td>
						<td>
							<time datetime={item.first_submitted_at}
								>{formatDate(item.first_submitted_at, formatContext)}</time
							>
							<br />
							<span class="hint"
								>{m.moderation_queue_rounds({
									count: item.rounds,
									date: formatDate(item.latest_round_at, formatContext)
								})}</span
							>
						</td>
						<td>
							<ul class="plain">
								{#if item.outdated.length > 0}
									<li><strong>{m.moderation_flag_outdated()}</strong></li>
								{/if}
								{#if item.overlapping.length > 0}
									<li>
										{m.moderation_flag_overlapping()}
										{#each item.overlapping as other, index (other)}
											{#if index > 0},
											{/if}<a href={submission(other)}
												>{m.moderation_submission_ref({ number: other })}</a
											>
										{/each}
									</li>
								{/if}
								{#if item.nearby_creates.length > 0}
									<li>
										{m.moderation_flag_nearby()}
										{#each item.nearby_creates as other, index (other)}
											{#if index > 0},
											{/if}<a href={submission(other)}
												>{m.moderation_submission_ref({ number: other })}</a
											>
										{/each}
									</li>
								{/if}
								{#if item.outdated.length === 0 && item.overlapping.length === 0 && item.nearby_creates.length === 0}
									<li class="hint">{m.moderation_queue_no_flags()}</li>
								{/if}
							</ul>
						</td>
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

	.filters h2 {
		font-size: 1.125rem;
	}

	.fields {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem 1.25rem;
	}

	.fields > div {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	label {
		font-weight: 700;
	}

	select,
	input,
	button {
		font: inherit;
		color: inherit;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 0.25rem;
		padding: 0.375rem 0.5rem;
	}

	input {
		inline-size: 10rem;
	}

	button {
		cursor: pointer;
	}

	.buttons {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.hint {
		color: var(--text-muted);
	}

	.plain {
		margin: 0.25rem 0 0;
		padding: 0;
		list-style: none;
		font-weight: 400;
	}

	th[scope='row'] .plain {
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
