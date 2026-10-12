<script lang="ts">
	import { onMount } from 'svelte';
	import { applyAction, enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import {
		PASSKEY_CANCELLED,
		callAction,
		createPasskey,
		passkeysSupported
	} from '#lib/auth/passkey.ts';
	import { formatDate } from '#lib/i18n/format.ts';
	import { m } from '#lib/paraglide/messages.js';
	import PageTitle from '#lib/shell/PageTitle.svelte';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();

	// Adding a passkey needs the browser's WebAuthn support, known only once the page runs.
	let support = $state<'unknown' | 'yes' | 'no'>('unknown');
	onMount(() => {
		support = passkeysSupported() ? 'yes' : 'no';
	});
	let name = $state('');
	let busy = $state(false);
	let localError = $state<string>();

	async function addPasskey(event: SubmitEvent) {
		event.preventDefault();
		busy = true;
		localError = undefined;
		try {
			const options = await callAction<{ options: PublicKeyCredentialCreationOptionsJSON }>(
				'passkeyOptions'
			);
			if (options.type !== 'success' || !options.data?.options) {
				await applyAction(options);
				return;
			}
			const credential = await createPasskey(options.data.options);
			if (credential === null) {
				localError = PASSKEY_CANCELLED;
				return;
			}
			const result = await callAction('addPasskey', { name, credential });
			await applyAction(result);
			if (result.type === 'success') {
				name = '';
				await invalidateAll();
			}
		} catch {
			localError = 'unknown';
		} finally {
			busy = false;
		}
	}

	const errorCode = $derived(localError ?? (form && 'error' in form ? form.error : undefined));
	const errorText = $derived.by(() => {
		switch (errorCode) {
			case undefined:
				return undefined;
			case 'passkey_invalid':
				return m.account_error_passkey_invalid();
			case PASSKEY_CANCELLED:
				return m.account_error_passkey_cancelled();
			case 'passkey_name_length':
				return m.account_error_passkey_name_length();
			case 'passkey_name_control_characters':
				return m.account_error_passkey_name_control_characters();
			case 'passkey_not_found':
				return m.account_error_passkey_not_found();
			default:
				return m.error_unknown();
		}
	});
	const nameError = $derived(errorCode?.startsWith('passkey_name_') ?? false);
	const statusText = $derived.by(() => {
		if (form && 'added' in form && form.added) return m.account_passkey_added({ name: form.added });
		if (form && 'removed' in form && form.removed !== undefined)
			return m.account_passkey_removed({ name: form.removed });
		return '';
	});
	const formatContext = $derived({ locale: data.locale, timeZone: data.timeZone });
</script>

<PageTitle title={m.account_title()} />

<h1>{m.account_title()}</h1>

<section class="passkeys" aria-labelledby="passkeys-heading">
	<h2 id="passkeys-heading">{m.account_passkeys_heading()}</h2>
	<p>{m.account_passkeys_intro()}</p>

	<p role="status">{statusText}</p>
	{#if errorText && !nameError}
		<p class="error" role="alert"><strong>{errorText}</strong></p>
	{/if}

	{#if data.passkeys.length === 0}
		<p>{m.account_passkeys_empty()}</p>
	{:else}
		<ul>
			{#each data.passkeys as passkey (passkey.id)}
				<li>
					<div>
						<strong id="passkey-{passkey.id}">{passkey.name}</strong>
						<span class="added">
							{m.account_passkey_added_on({ date: formatDate(passkey.created_at, formatContext) })}
						</span>
					</div>
					<form method="post" action="?/removePasskey" use:enhance>
						<input type="hidden" name="id" value={passkey.id} />
						<input type="hidden" name="name" value={passkey.name} />
						<button type="submit" aria-describedby="passkey-{passkey.id}">
							{m.account_passkey_remove()}
						</button>
					</form>
				</li>
			{/each}
		</ul>
	{/if}

	<h3>{m.account_passkey_add_heading()}</h3>
	{#if support === 'yes'}
		{#if errorText && nameError}
			<p class="error" id="passkey-name-error" role="alert"><strong>{errorText}</strong></p>
		{/if}
		<form method="post" action="?/addPasskey" onsubmit={addPasskey}>
			<label for="passkey-name">{m.account_passkey_name_label()}</label>
			<p class="hint" id="passkey-name-hint">{m.account_passkey_name_hint()}</p>
			<input
				id="passkey-name"
				name="name"
				type="text"
				autocomplete="off"
				required
				maxlength="200"
				bind:value={name}
				aria-invalid={nameError ? 'true' : undefined}
				aria-describedby={nameError ? 'passkey-name-error passkey-name-hint' : 'passkey-name-hint'}
			/>
			<button type="submit" disabled={busy}>{m.account_passkey_add_submit()}</button>
		</form>
	{:else if support === 'no'}
		<p>{m.account_passkeys_unsupported()}</p>
	{/if}
	<noscript><p>{m.account_passkeys_unsupported()}</p></noscript>
</section>

<style>
	.passkeys {
		max-inline-size: 40rem;
	}

	ul {
		list-style: none;
		padding: 0;
	}

	li {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem 1rem;
		padding-block: 0.75rem;
		border-block-end: 1px solid var(--border);
	}

	li div {
		display: flex;
		flex-direction: column;
	}

	.added,
	.hint {
		color: var(--text-muted);
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

	/* An error is said in words and marked with a border, never by colour alone. */
	.error {
		border-inline-start: 4px solid currentColor;
		padding-inline-start: 0.75rem;
	}

	[aria-invalid='true'] {
		border-width: 2px;
		border-color: currentColor;
	}
</style>
