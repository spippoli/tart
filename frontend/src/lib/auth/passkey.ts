import { deserialize } from '$app/forms';

/**
 * Passkeys in the browser (Foundations spec, 2. Sign-in): the page asks its own form
 * action for WebAuthn options, which the server gets from the API, lets the browser
 * create or use a passkey, and posts the result to another action. Passkeys need
 * JavaScript and a browser with WebAuthn's JSON methods; without them the page
 * offers the email code alone.
 */

/** The error code of a passkey the person did not create or use: cancelled or timed out. */
export const PASSKEY_CANCELLED = 'passkey_cancelled';

export function passkeysSupported(): boolean {
	return (
		typeof PublicKeyCredential !== 'undefined' &&
		'parseCreationOptionsFromJSON' in PublicKeyCredential &&
		'parseRequestOptionsFromJSON' in PublicKeyCredential
	);
}

/** Post to one of the page's form actions, as `use:enhance` would. */
export async function callAction<Success extends Record<string, unknown> | undefined = undefined>(
	action: string,
	fields: Record<string, string> = {}
): Promise<ReturnType<typeof deserialize<Success, Record<string, unknown>>>> {
	const body = new FormData();
	for (const [name, value] of Object.entries(fields)) body.set(name, value);
	const response = await fetch(`?/${action}`, {
		method: 'POST',
		body,
		headers: { 'x-sveltekit-action': 'true' }
	});
	return deserialize(await response.text());
}

/** A credential in WebAuthn's JSON form, or null if the person did not go through with it. */
async function credentialJson(ceremony: () => Promise<Credential | null>): Promise<string | null> {
	try {
		const credential = await ceremony();
		return credential instanceof PublicKeyCredential ? JSON.stringify(credential.toJSON()) : null;
	} catch (error) {
		// Cancelled, timed out, or a passkey this site already has: nothing was made.
		if (error instanceof DOMException) return null;
		throw error;
	}
}

export function createPasskey(options: PublicKeyCredentialCreationOptionsJSON) {
	return credentialJson(() =>
		navigator.credentials.create({
			publicKey: PublicKeyCredential.parseCreationOptionsFromJSON(options)
		})
	);
}

export function usePasskey(options: PublicKeyCredentialRequestOptionsJSON) {
	return credentialJson(() =>
		navigator.credentials.get({
			publicKey: PublicKeyCredential.parseRequestOptionsFromJSON(options)
		})
	);
}
