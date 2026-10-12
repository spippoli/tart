<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { applyAction, enhance, type SubmitFunction } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import {
		PASSKEY_CANCELLED,
		callAction,
		createPasskey,
		passkeysSupported
	} from '#lib/auth/passkey.ts';
	import { formatDate, formatWait } from '#lib/i18n/format.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { isLocale } from '#lib/paraglide/runtime.js';
	import PageTitle from '#lib/shell/PageTitle.svelte';
	import type { PageProps } from './$types';
	import type { Section } from './+page.server';

	let { data, form }: PageProps = $props();

	/** The outcome of the last action, if it belongs to `section`. */
	function outcome(section: Section) {
		return form && 'section' in form && form.section === section ? form : undefined;
	}
	const nameOutcome = $derived(outcome('name'));
	const languageOutcome = $derived(outcome('language'));
	const emailOutcome = $derived(outcome('email'));
	const passkeyOutcome = $derived(outcome('passkeys'));

	function errorOf(result: object | undefined): string | undefined {
		return result && 'error' in result ? String(result.error) : undefined;
	}

	// Keep what was entered: a saved setting comes back from the reloaded data.
	const keepValues: SubmitFunction = () => {
		return async ({ update }) => update({ reset: false });
	};

	const nameError = $derived.by(() => {
		switch (errorOf(nameOutcome)) {
			case undefined:
				return undefined;
			case 'display_name_length':
				return m.sign_in_error_display_name_length();
			case 'display_name_control_characters':
				return m.sign_in_error_display_name_control_characters();
			case 'display_name_reserved':
				return m.sign_in_error_display_name_reserved();
			default:
				return m.error_unknown();
		}
	});
	const nameValue = $derived(
		nameOutcome && 'display_name' in nameOutcome && typeof nameOutcome.display_name === 'string'
			? nameOutcome.display_name
			: data.account.display_name
	);

	const languages = $derived(data.languages.filter(isLocale));
	const languageError = $derived.by(() => {
		switch (errorOf(languageOutcome)) {
			case undefined:
				return undefined;
			case 'language_unavailable':
				return m.account_error_language_unavailable();
			default:
				return m.error_unknown();
		}
	});

	const emailStep = $derived(
		emailOutcome && 'step' in emailOutcome && emailOutcome.step === 'code' ? 'code' : 'email'
	);
	const newEmail = $derived(
		emailOutcome && 'email' in emailOutcome ? String(emailOutcome.email ?? '') : ''
	);
	const emailError = $derived.by(() => {
		switch (errorOf(emailOutcome)) {
			case undefined:
				return undefined;
			case 'email_invalid':
				return m.sign_in_error_email_invalid();
			case 'email_unchanged':
				return m.account_error_email_unchanged();
			case 'code_invalid':
				return m.sign_in_error_code_invalid();
			case 'rate_limited':
				return m.sign_in_error_rate_limited({
					when: formatWait(
						emailOutcome && 'retryAfter' in emailOutcome ? Number(emailOutcome.retryAfter) : 60,
						{ locale: data.locale }
					)
				});
			default:
				return m.error_unknown();
		}
	});
	const emailStatus = $derived.by(() => {
		if (emailOutcome && 'changed' in emailOutcome && emailOutcome.changed) {
			return m.account_email_changed({ email: emailOutcome.changed });
		}
		if (emailStep === 'code' && !emailError) return m.account_email_code_sent({ email: newEmail });
		return '';
	});
	// The next step's field takes the focus, as a new page would put the reader there.
	const emailSubmit: SubmitFunction = () => {
		return async ({ update }) => {
			await update();
			await tick();
			document
				.querySelector<HTMLInputElement>('#email-section [aria-invalid], #email-code')
				?.focus();
		};
	};

	// Adding a passkey needs the browser's WebAuthn support, known only once the page runs.
	let support = $state<'unknown' | 'yes' | 'no'>('unknown');
	onMount(() => {
		support = passkeysSupported() ? 'yes' : 'no';
	});
	let passkeyName = $state('');
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
			const result = await callAction('addPasskey', { name: passkeyName, credential });
			await applyAction(result);
			if (result.type === 'success') {
				passkeyName = '';
				await invalidateAll();
			}
		} catch {
			localError = 'unknown';
		} finally {
			busy = false;
		}
	}

	const passkeyErrorCode = $derived(localError ?? errorOf(passkeyOutcome));
	const passkeyError = $derived.by(() => {
		switch (passkeyErrorCode) {
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
	const passkeyNameError = $derived(passkeyErrorCode?.startsWith('passkey_name_') ?? false);
	const passkeyStatus = $derived.by(() => {
		if (passkeyOutcome && 'added' in passkeyOutcome && passkeyOutcome.added) {
			return m.account_passkey_added({ name: passkeyOutcome.added });
		}
		if (passkeyOutcome && 'removed' in passkeyOutcome && passkeyOutcome.removed !== undefined) {
			return m.account_passkey_removed({ name: passkeyOutcome.removed });
		}
		return '';
	});
	const formatContext = $derived({ locale: data.locale, timeZone: data.timeZone });
</script>

<PageTitle title={m.account_title()} />

<h1>{m.account_title()}</h1>

<section aria-labelledby="name-heading">
	<h2 id="name-heading">{m.account_name_heading()}</h2>
	<p>{m.account_name_intro()}</p>
	<p role="status">{nameOutcome && 'saved' in nameOutcome ? m.account_name_saved() : ''}</p>
	{#if nameError}
		<p class="error" id="display-name-error" role="alert"><strong>{nameError}</strong></p>
	{/if}
	<form method="post" action="?/displayName" use:enhance={keepValues}>
		<label for="display-name">{m.account_name_label()}</label>
		<p class="hint" id="display-name-hint">{m.account_name_hint()}</p>
		<!-- A display name is the User's own text, in no particular language. -->
		<input
			id="display-name"
			name="display_name"
			type="text"
			lang=""
			autocomplete="nickname"
			required
			maxlength="200"
			value={nameValue}
			aria-invalid={nameError ? 'true' : undefined}
			aria-describedby={nameError ? 'display-name-error display-name-hint' : 'display-name-hint'}
		/>
		<button type="submit">{m.account_name_submit()}</button>
	</form>
</section>

<section aria-labelledby="language-heading">
	<h2 id="language-heading">{m.account_language_heading()}</h2>
	<p role="status">
		{languageOutcome && 'saved' in languageOutcome ? m.account_language_saved() : ''}
	</p>
	{#if languageError}
		<p class="error" role="alert"><strong>{languageError}</strong></p>
	{/if}
	<form method="post" action="?/language" use:enhance={keepValues}>
		<label for="language">{m.account_language_label()}</label>
		<p class="hint" id="language-hint">{m.account_language_hint()}</p>
		<select id="language" name="language" aria-describedby="language-hint">
			{#each languages as language (language)}
				<!-- Each language is named in itself, as in the language switcher. -->
				<option
					value={language}
					lang={language}
					selected={language === data.account.preferred_language}
				>
					{m.language_name({}, { locale: language })}
				</option>
			{/each}
		</select>
		<button type="submit">{m.account_language_submit()}</button>
	</form>
</section>

<section id="email-section" aria-labelledby="email-heading">
	<h2 id="email-heading">{m.account_email_heading()}</h2>
	<p>{m.account_email_current({ email: data.account.email })}</p>
	<p role="status">{emailStatus}</p>
	{#if emailError}
		<p class="error" id="email-error" role="alert"><strong>{emailError}</strong></p>
	{/if}
	{#if emailStep === 'code'}
		<form method="post" action="?/confirmEmailChange" use:enhance={emailSubmit}>
			<input type="hidden" name="email" value={newEmail} />
			<label for="email-code">{m.sign_in_code_label()}</label>
			<input
				id="email-code"
				name="code"
				type="text"
				inputmode="numeric"
				autocomplete="one-time-code"
				pattern="[0-9]*"
				required
				aria-invalid={emailError ? 'true' : undefined}
				aria-describedby={emailError ? 'email-error' : undefined}
			/>
			<button type="submit">{m.account_email_code_submit()}</button>
		</form>
		<p><a href="?">{m.account_email_other()}</a></p>
	{:else}
		<form method="post" action="?/requestEmailChange" use:enhance={emailSubmit}>
			<label for="new-email">{m.account_email_label()}</label>
			<p class="hint" id="new-email-hint">{m.account_email_hint()}</p>
			<input
				id="new-email"
				name="email"
				type="email"
				autocomplete="email"
				required
				value={(emailError && newEmail) || undefined}
				aria-invalid={emailError ? 'true' : undefined}
				aria-describedby={emailError ? 'email-error new-email-hint' : 'new-email-hint'}
			/>
			<button type="submit">{m.account_email_submit()}</button>
		</form>
	{/if}
</section>

<section class="passkeys" aria-labelledby="passkeys-heading">
	<h2 id="passkeys-heading">{m.account_passkeys_heading()}</h2>
	<p>{m.account_passkeys_intro()}</p>

	<p role="status">{passkeyStatus}</p>
	{#if passkeyError && !passkeyNameError}
		<p class="error" role="alert"><strong>{passkeyError}</strong></p>
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
		{#if passkeyError && passkeyNameError}
			<p class="error" id="passkey-name-error" role="alert"><strong>{passkeyError}</strong></p>
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
				bind:value={passkeyName}
				aria-invalid={passkeyNameError ? 'true' : undefined}
				aria-describedby={passkeyNameError
					? 'passkey-name-error passkey-name-hint'
					: 'passkey-name-hint'}
			/>
			<button type="submit" disabled={busy}>{m.account_passkey_add_submit()}</button>
		</form>
	{:else if support === 'no'}
		<p>{m.account_passkeys_unsupported()}</p>
	{/if}
	<noscript><p>{m.account_passkeys_unsupported()}</p></noscript>
</section>

<section aria-labelledby="sessions-heading">
	<h2 id="sessions-heading">{m.account_sessions_heading()}</h2>
	<p>{m.account_sessions_intro()}</p>
	<form method="post" action="?/signOutEverywhere">
		<button type="submit">{m.account_sign_out_everywhere()}</button>
	</form>
</section>

<style>
	section {
		max-inline-size: 40rem;
		margin-block-end: 2.5rem;
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
	select,
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
