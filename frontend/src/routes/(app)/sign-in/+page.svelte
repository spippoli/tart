<script lang="ts">
	import { onMount } from 'svelte';
	import { applyAction } from '$app/forms';
	import {
		PASSKEY_CANCELLED,
		callAction,
		passkeysSupported,
		usePasskey
	} from '#lib/auth/passkey.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { getLocale, localizeHref } from '#lib/paraglide/runtime.js';
	import PageTitle from '#lib/shell/PageTitle.svelte';
	import type { PageProps } from './$types';
	import type { Step } from './+page.server';

	let { data, form }: PageProps = $props();

	const step: Step = $derived(form?.step ?? 'email');
	const email = $derived(form?.email ?? '');
	// The visible fields get a value only when there is one to restore: an empty one
	// would clear, at hydration, what the person typed before the page was ready.
	// The return page rides on every form's URL, so that each step keeps it.
	const query = $derived(data.next ? `&next=${encodeURIComponent(data.next)}` : '');
	const restart = $derived(
		localizeHref('/sign-in') + (data.next ? `?next=${encodeURIComponent(data.next)}` : '')
	);

	const registrationText = $derived(
		{
			open: m.sign_in_registration_open,
			invite: m.sign_in_registration_invite,
			closed: m.sign_in_registration_closed
		}[data.registration]
	);

	/** "in 5 minutes", in the UI language. */
	function waitText(seconds: number): string {
		const format = new Intl.RelativeTimeFormat(getLocale(), { numeric: 'auto' });
		if (seconds < 60) return format.format(seconds, 'second');
		if (seconds < 3600) return format.format(Math.ceil(seconds / 60), 'minute');
		return format.format(Math.ceil(seconds / 3600), 'hour');
	}

	// Passkeys need the browser's WebAuthn support, known only once the page runs.
	let canUsePasskey = $state(false);
	onMount(() => {
		canUsePasskey = passkeysSupported();
	});
	let passkeyBusy = $state(false);
	let passkeyError = $state<string>();

	async function signInWithPasskey() {
		passkeyBusy = true;
		passkeyError = undefined;
		try {
			const options = await callAction<{ options: PublicKeyCredentialRequestOptionsJSON }>(
				'passkeyOptions'
			);
			if (options.type !== 'success' || !options.data?.options) {
				passkeyError = 'unknown';
				return;
			}
			const credential = await usePasskey(options.data.options);
			if (credential === null) {
				passkeyError = PASSKEY_CANCELLED;
				return;
			}
			// A redirect signs in and goes on; a failure sets `form` with its error code.
			await applyAction(await callAction('passkeySignIn', { credential, next: data.next ?? '' }));
		} catch {
			passkeyError = 'unknown';
		} finally {
			passkeyBusy = false;
		}
	}

	const errorCode = $derived(passkeyError ?? form?.error);
	const passkeyFailure = $derived(
		passkeyError !== undefined || (errorCode?.startsWith('passkey_') ?? false)
	);

	const errorText = $derived.by(() => {
		if (!errorCode) return undefined;
		switch (errorCode) {
			case 'email_invalid':
				return m.sign_in_error_email_invalid();
			case 'code_invalid':
				return m.sign_in_error_code_invalid();
			case 'rate_limited':
				return m.sign_in_error_rate_limited({
					when: waitText(form && 'retryAfter' in form ? Number(form.retryAfter) : 60)
				});
			case 'age_not_confirmed':
				return m.sign_in_error_age_not_confirmed({ age: data.minAge });
			case 'display_name_length':
				return m.sign_in_error_display_name_length();
			case 'display_name_control_characters':
				return m.sign_in_error_display_name_control_characters();
			case 'display_name_reserved':
				return m.sign_in_error_display_name_reserved();
			case 'passkey_invalid':
				return m.sign_in_error_passkey_invalid();
			case PASSKEY_CANCELLED:
				return m.sign_in_error_passkey_cancelled();
			default:
				return m.error_unknown();
		}
	});
	const ageError = $derived(form?.error === 'age_not_confirmed');
	const nameError = $derived(form?.error?.startsWith('display_name_') ?? false);
</script>

<PageTitle title={m.sign_in_title()} />

<h1>{m.sign_in_title()}</h1>

{#snippet error(id: string)}
	{#if errorText}
		<p class="error" {id} role="alert"><strong>{errorText}</strong></p>
	{/if}
{/snippet}

<div class="sign-in">
	{#if step === 'email'}
		<p>{m.sign_in_intro()}</p>
		<p>{registrationText()}</p>
		{#if !passkeyFailure}{@render error('email-error')}{/if}
		<form method="post" action="?/request{query}">
			<label for="email">{m.sign_in_email_label()}</label>
			<input
				id="email"
				name="email"
				type="email"
				autocomplete="email"
				required
				value={email || undefined}
				aria-invalid={errorText && !passkeyFailure ? 'true' : undefined}
				aria-describedby={errorText && !passkeyFailure ? 'email-error' : undefined}
			/>
			<!-- The honeypot: people leave it empty (Foundations spec, spam protection). -->
			<div class="honeypot">
				<label for="website">{m.sign_in_honeypot_label()}</label>
				<input id="website" name="website" type="text" tabindex="-1" autocomplete="off" />
			</div>
			<button type="submit">{m.sign_in_send_code()}</button>
		</form>
		{#if canUsePasskey}
			<section aria-labelledby="passkey-heading">
				<h2 id="passkey-heading">{m.sign_in_passkey_heading()}</h2>
				<p>{m.sign_in_passkey_intro()}</p>
				{#if passkeyFailure}{@render error('passkey-error')}{/if}
				<button type="button" onclick={signInWithPasskey} disabled={passkeyBusy}>
					{m.sign_in_passkey_submit()}
				</button>
			</section>
		{/if}
	{:else if step === 'code'}
		<p>{m.sign_in_code_sent({ email })}</p>
		{@render error('code-error')}
		<form method="post" action="?/verify{query}">
			<input type="hidden" name="email" value={email} />
			<label for="code">{m.sign_in_code_label()}</label>
			<input
				id="code"
				name="code"
				type="text"
				inputmode="numeric"
				autocomplete="one-time-code"
				required
				aria-invalid={errorText ? 'true' : undefined}
				aria-describedby={errorText ? 'code-error' : undefined}
			/>
			<button type="submit">{m.sign_in_submit()}</button>
		</form>
		<form method="post" action="?/request{query}" class="secondary">
			<input type="hidden" name="email" value={email} />
			<button type="submit">{m.sign_in_new_code()}</button>
		</form>
		<p><a href={restart}>{m.sign_in_other_address()}</a></p>
	{:else}
		<h2>{m.sign_in_register_heading()}</h2>
		<p>{m.sign_in_register_intro({ email })}</p>
		{@render error('register-error')}
		<form method="post" action="?/register{query}">
			<input type="hidden" name="email" value={email} />
			<input type="hidden" name="code" value={form?.code ?? ''} />
			<label for="display-name">{m.sign_in_display_name_label()}</label>
			<p class="hint" id="display-name-hint">{m.sign_in_display_name_hint()}</p>
			<input
				id="display-name"
				name="display_name"
				type="text"
				autocomplete="nickname"
				required
				maxlength="200"
				value={(form && 'displayName' in form && form.displayName) || undefined}
				aria-invalid={nameError ? 'true' : undefined}
				aria-describedby={nameError ? 'register-error display-name-hint' : 'display-name-hint'}
			/>
			<div class="checkbox">
				<input
					id="age-confirmed"
					name="age_confirmed"
					type="checkbox"
					required
					aria-invalid={ageError ? 'true' : undefined}
					aria-describedby={ageError ? 'register-error' : undefined}
				/>
				<label for="age-confirmed">{m.sign_in_age_label({ age: data.minAge })}</label>
			</div>
			<button type="submit">{m.sign_in_register_submit()}</button>
		</form>
	{/if}
</div>

<style>
	.sign-in {
		max-inline-size: 32rem;
	}

	form {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 0.5rem;
		margin-block: 1rem;
	}

	label {
		font-weight: 700;
	}

	.checkbox {
		display: flex;
		align-items: baseline;
		gap: 0.5rem;
	}

	.checkbox label {
		font-weight: 400;
	}

	input:not([type='checkbox']),
	button {
		font: inherit;
		color: inherit;
		background: var(--background);
		border: 1px solid var(--border);
		border-radius: 0.25rem;
		padding: 0.375rem 0.5rem;
	}

	input:not([type='checkbox']) {
		inline-size: 100%;
		box-sizing: border-box;
	}

	button {
		background: var(--surface);
		cursor: pointer;
	}

	.hint {
		margin: 0;
		color: var(--text-muted);
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

	.honeypot {
		position: absolute;
		inset-inline-start: -10000px;
		inline-size: 1px;
		block-size: 1px;
		overflow: hidden;
	}
</style>
