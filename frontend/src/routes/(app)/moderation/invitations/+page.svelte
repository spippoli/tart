<script lang="ts">
	import { onMount } from 'svelte';
	import { enhance } from '$app/forms';
	import { page } from '$app/state';
	import { formatDate } from '#lib/i18n/format.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { localizeHref } from '#lib/paraglide/runtime.js';
	import PageTitle from '#lib/shell/PageTitle.svelte';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();

	const formatContext = $derived({ locale: data.locale, timeZone: data.timeZone });

	function outcome(section: 'issue' | 'list') {
		return form && 'section' in form && form.section === section ? form : undefined;
	}
	const issueOutcome = $derived(outcome('issue'));
	const listOutcome = $derived(outcome('list'));

	const errors: Record<string, () => string> = {
		email_invalid: m.invitations_error_email_invalid,
		invitation_pending: m.invitations_error_invitation_pending,
		registration_not_invite: m.invitations_error_registration_not_invite,
		invitation_not_found: m.invitations_error_invitation_not_found,
		invitation_not_pending: m.invitations_error_invitation_not_pending
	};
	function errorText(result: object | undefined): string | undefined {
		if (!result || !('error' in result)) return undefined;
		return (errors[String(result.error)] ?? m.error_unknown)();
	}
	const issueError = $derived(errorText(issueOutcome));
	const listError = $derived(errorText(listOutcome));

	const issued = $derived(
		issueOutcome && 'issued' in issueOutcome ? issueOutcome.issued : undefined
	);
	const issuedEmail = $derived(
		issueOutcome && 'email' in issueOutcome ? String(issueOutcome.email ?? '') : ''
	);
	const revokedEmail = $derived(
		listOutcome && 'revoked' in listOutcome ? String(listOutcome.revoked) : undefined
	);

	// The Invitation is redeemed on the sign-in page, in the language of this one.
	const link = $derived(new URL(localizeHref('/sign-in'), page.url.origin).href);

	// Copying needs JavaScript and the clipboard; the link is shown in any case.
	let canCopy = $state(false);
	let copied = $state(false);
	onMount(() => {
		canCopy = typeof navigator !== 'undefined' && !!navigator.clipboard;
	});
	async function copy() {
		await navigator.clipboard.writeText(link);
		copied = true;
	}

	const statusLabel = {
		pending: m.invitations_status_pending,
		used: m.invitations_status_used,
		expired: m.invitations_status_expired,
		revoked: m.invitations_status_revoked
	};
	function dateText(invitation: (typeof data.invitations)[number]): string {
		const date = (instant: string) => formatDate(instant, formatContext);
		switch (invitation.status) {
			case 'pending':
				return m.invitations_date_pending({ date: date(invitation.expires_at) });
			case 'used':
				return m.invitations_date_used({ date: date(invitation.used_at ?? invitation.created_at) });
			case 'revoked':
				return m.invitations_date_revoked({
					date: date(invitation.revoked_at ?? invitation.created_at)
				});
			default:
				return m.invitations_date_expired({ date: date(invitation.expires_at) });
		}
	}
</script>

<PageTitle title={m.invitations_title()} />

<h1>{m.invitations_title()}</h1>
<p class="intro">{m.invitations_intro()}</p>

<section aria-labelledby="issue-heading">
	<h2 id="issue-heading">{m.invitations_issue_heading()}</h2>
	{#if issueError}
		<p class="error" id="issue-error" role="alert"><strong>{issueError}</strong></p>
	{/if}
	<form method="post" action="?/issue" use:enhance>
		<label for="invitation-email">{m.invitations_email_label()}</label>
		<p class="hint" id="invitation-email-hint">{m.invitations_email_hint()}</p>
		<input
			id="invitation-email"
			name="email"
			type="email"
			autocomplete="off"
			required
			value={issueError ? issuedEmail : ''}
			aria-invalid={issueError ? 'true' : undefined}
			aria-describedby={issueError ? 'issue-error invitation-email-hint' : 'invitation-email-hint'}
		/>
		<button type="submit">{m.invitations_issue_submit()}</button>
	</form>
	<div role="status">
		{#if issued}
			<p>
				{m.invitations_issued({
					email: issued.email,
					date: formatDate(issued.expiresAt, formatContext)
				})}
			</p>
			<label for="invitation-link">{m.invitations_link_label()}</label>
			<input id="invitation-link" type="text" readonly value={link} />
			{#if canCopy}
				<button type="button" onclick={copy}>{m.invitations_copy()}</button>
			{/if}
			{#if copied}<p>{m.invitations_copied()}</p>{/if}
		{/if}
	</div>
</section>

<section aria-labelledby="list-heading">
	<h2 id="list-heading">{m.invitations_list_heading()}</h2>
	<p role="status">
		{revokedEmail === undefined ? '' : m.invitations_revoked({ email: revokedEmail })}
	</p>
	{#if listError}
		<p class="error" role="alert"><strong>{listError}</strong></p>
	{/if}
	{#if data.invitations.length === 0}
		<p>{m.invitations_empty()}</p>
	{:else}
		<!-- A table wider than the screen scrolls, so keyboard users must be able to focus it. -->
		<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
		<div class="scroll" role="region" aria-labelledby="list-heading" tabindex="0">
			<table>
				<caption class="visually-hidden">{m.invitations_caption()}</caption>
				<thead>
					<tr>
						<th scope="col">{m.invitations_column_email()}</th>
						<th scope="col">{m.invitations_column_status()}</th>
						<th scope="col">{m.invitations_column_date()}</th>
						<th scope="col">{m.invitations_column_issuer()}</th>
						<th scope="col">{m.invitations_column_actions()}</th>
					</tr>
				</thead>
				<tbody>
					{#each data.invitations as invitation (invitation.id)}
						<tr>
							<th scope="row" id="invitation-{invitation.id}">{invitation.email}</th>
							<td>{statusLabel[invitation.status]()}</td>
							<td>{dateText(invitation)}</td>
							<td>
								{#if invitation.issuer}
									{m.invitations_issuer({
										name: invitation.issuer.display_name,
										number: invitation.issuer.number
									})}
								{:else}
									{m.invitations_issuer_operator()}
								{/if}
							</td>
							<td>
								{#if invitation.status === 'pending'}
									<form method="post" action="?/revoke" use:enhance>
										<input type="hidden" name="id" value={invitation.id} />
										<input type="hidden" name="email" value={invitation.email} />
										<button type="submit" aria-describedby="invitation-{invitation.id}">
											{m.invitations_revoke()}
										</button>
									</form>
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</section>

<style>
	.intro,
	section > form {
		max-inline-size: 40rem;
	}

	section {
		margin-block-end: 2.5rem;
	}

	form {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 0.5rem;
	}

	label {
		font-weight: 700;
	}

	.hint {
		margin: 0;
		color: var(--text-muted);
	}

	input,
	button {
		font: inherit;
		color: inherit;
		background: var(--background);
		border: 1px solid var(--border);
		border-radius: 0.25rem;
		padding: 0.375rem 0.5rem;
	}

	input {
		inline-size: 100%;
		box-sizing: border-box;
	}

	button {
		background: var(--surface);
		cursor: pointer;
	}

	[role='status'] input {
		max-inline-size: 40rem;
	}

	/* An error is said in words and marked with a border, never by colour alone. */
	.error {
		border-inline-start: 4px solid currentColor;
		padding-inline-start: 0.75rem;
	}

	[aria-invalid='true'] {
		border-width: 2px;
		border-color: currentColor;
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
