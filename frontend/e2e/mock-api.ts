/**
 * A stand-in for the `api` service in the end-to-end tests: it answers
 * `GET /api/config` with a fictional public configuration. Under the `/it-only`
 * prefix, the same configuration enables Italian alone, for a second frontend
 * server that tests a disabled UI language.
 *
 * It also stands in for sign-in (`/api/auth/*`), with fixed rules instead of the
 * API's: every code is `123456`; `persona@…` and `moderatrice@…` (the Moderator)
 * are Users from the start, any other address registers; `limitata@…` is rate
 * limited; the session token is the address. It refuses a state-changing request
 * without the CSRF header or the client IP, as the API would not know the IP.
 * Passkeys are kept by credential id and checked for nothing else: the browser's
 * virtual authenticator makes them, and the API's own tests verify them.
 *
 *     node e2e/mock-api.ts [port]
 */
import { createHash, randomBytes } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';

const config = JSON.parse(readFileSync(new URL('fixtures/config.json', import.meta.url), 'utf8'));
const variants: Record<string, unknown> = {
	'/api/config': config,
	'/it-only/api/config': { ...config, languages: { ...config.languages, ui: ['it'] } }
};

const CODE = '123456';
const users = new Map<string, { display_name: string; moderator: boolean; language: string }>();

function isPreset(email: string) {
	const local = email.split('@')[0];
	return local.startsWith('persona') || local.startsWith('moderatrice');
}

interface Passkey {
	id: number;
	name: string;
	created_at: string;
	credentialId: string;
	email: string;
}
const passkeys: Passkey[] = [];
let nextPasskeyId = 1;

function sessionEmail(request: IncomingMessage): string | null {
	const token = /(?:^|;\s*)tart_session=([^;]+)/.exec(request.headers.cookie ?? '')?.[1];
	return token ? decodeURIComponent(token) : null;
}

function sessionUser(request: IncomingMessage) {
	const email = sessionEmail(request);
	if (!email) return null;
	if (!users.has(email) && isPreset(email)) {
		users.set(email, {
			display_name: email.startsWith('moderatrice') ? 'Moderatrice di prova' : 'Persona di prova',
			moderator: email.startsWith('moderatrice'),
			language: 'it'
		});
	}
	const user = users.get(email);
	return user ? { number: 1, preferred_language: user.language, ...user } : null;
}

async function readJson(request: IncomingMessage) {
	let body = '';
	for await (const chunk of request) body += chunk;
	return JSON.parse(body || '{}');
}

function send(response: ServerResponse, status: number, body?: unknown, headers = {}) {
	response
		.writeHead(status, { 'Content-Type': 'application/json', ...headers })
		.end(body === undefined ? undefined : JSON.stringify(body));
}

const signedIn = (email: string) => ({
	'Set-Cookie': `tart_session=${encodeURIComponent(email)}; HttpOnly; Max-Age=7776000; Path=/; SameSite=lax; Secure`
});

async function auth(request: IncomingMessage, response: ServerResponse, path: string) {
	if (path === '/api/auth/session' && request.method === 'GET') {
		return send(response, 200, { user: sessionUser(request) });
	}
	if (path === '/api/auth/passkeys' && request.method === 'GET') {
		const email = sessionUser(request) && sessionEmail(request);
		if (!email) return send(response, 401, { code: 'sign_in_required' });
		const own = passkeys.filter((key) => key.email === email);
		return send(
			response,
			200,
			own.map(({ id, name, created_at }) => ({ id, name, created_at }))
		);
	}
	if (
		(request.method !== 'POST' && request.method !== 'DELETE') ||
		!request.headers['x-tart-request'] ||
		!request.headers['x-tart-client-ip']
	) {
		return send(response, 403, { code: 'csrf_refused' });
	}
	if (path === '/api/auth/sign-out') return send(response, 204, undefined, signedIn(''));
	const body = await readJson(request);
	if (path.startsWith('/api/auth/passkey')) return passkey(request, response, path, body);
	const email = String(body.email ?? '').toLowerCase();
	if (path === '/api/auth/code') {
		if (!email.includes('@')) return send(response, 400, { code: 'email_invalid' });
		if (email.startsWith('limitata')) {
			return send(response, 429, { code: 'rate_limited', retry_after: 240 });
		}
		return send(response, 202, {});
	}
	if (path === '/api/auth/code/verify') {
		if (body.code !== CODE) return send(response, 400, { code: 'code_invalid' });
		if (isPreset(email) || users.has(email)) {
			return send(response, 200, { outcome: 'signed_in' }, signedIn(email));
		}
		const registration = body.registration;
		if (!registration) return send(response, 200, { outcome: 'registration_required' });
		if (!registration.age_confirmed) return send(response, 400, { code: 'age_not_confirmed' });
		const name = String(registration.display_name).trim();
		if (name.length < 1 || name.length > 40) {
			return send(response, 400, { code: 'display_name_length' });
		}
		if (/^(deleted user|utente eliminato) \d+$/i.test(name)) {
			return send(response, 400, { code: 'display_name_reserved' });
		}
		users.set(email, { display_name: name, moderator: false, language: body.language });
		return send(response, 200, { outcome: 'signed_in' }, signedIn(email));
	}
	send(response, 404);
}

const challenge = () => randomBytes(32).toString('base64url');

async function passkey(
	request: IncomingMessage,
	response: ServerResponse,
	path: string,
	body: Record<string, unknown>
) {
	if (path === '/api/auth/passkey/options') {
		return send(response, 200, {
			challenge: challenge(),
			timeout: 300000,
			rpId: 'localhost',
			allowCredentials: [],
			userVerification: 'required'
		});
	}
	if (path === '/api/auth/passkey/verify') {
		const credential = body.credential as { rawId?: string } | undefined;
		const found = passkeys.find((key) => key.credentialId === credential?.rawId);
		if (!found) return send(response, 400, { code: 'passkey_invalid' });
		return send(response, 200, { outcome: 'signed_in' }, signedIn(found.email));
	}
	const email = sessionUser(request) && sessionEmail(request);
	if (!email) return send(response, 401, { code: 'sign_in_required' });
	if (path === '/api/auth/passkeys/options') {
		return send(response, 200, {
			rp: { id: 'localhost', name: 'Archivio di prova' },
			user: {
				// WebAuthn allows at most 64 bytes.
				id: createHash('sha256').update(email).digest('base64url'),
				name: email,
				displayName: email
			},
			challenge: challenge(),
			pubKeyCredParams: [{ type: 'public-key', alg: -7 }],
			timeout: 300000,
			excludeCredentials: passkeys
				.filter((key) => key.email === email)
				.map((key) => ({ type: 'public-key', id: key.credentialId })),
			authenticatorSelection: { residentKey: 'required', userVerification: 'required' },
			attestation: 'none'
		});
	}
	if (path === '/api/auth/passkeys' && request.method === 'POST') {
		const name = String(body.name ?? '').trim();
		if (name.length < 1 || name.length > 40) {
			return send(response, 400, { code: 'passkey_name_length' });
		}
		const credential = body.credential as { rawId: string };
		const added = {
			id: nextPasskeyId++,
			name,
			created_at: new Date().toISOString(),
			credentialId: credential.rawId,
			email
		};
		passkeys.push(added);
		return send(response, 201, { id: added.id, name, created_at: added.created_at });
	}
	const removal = /^\/api\/auth\/passkeys\/(\d+)$/.exec(path);
	if (removal && request.method === 'DELETE') {
		const index = passkeys.findIndex((key) => key.id === Number(removal[1]) && key.email === email);
		if (index < 0) return send(response, 404, { code: 'passkey_not_found' });
		passkeys.splice(index, 1);
		return send(response, 204);
	}
	send(response, 404);
}

const port = Number(process.argv[2] ?? 8795);
createServer((request, response) => {
	const path = (request.url ?? '').replace(/^\/it-only/, '');
	if (path.startsWith('/api/auth/')) {
		auth(request, response, path).catch(() => send(response, 500));
		return;
	}
	const body = variants[request.url ?? ''];
	if (request.method !== 'GET' || body === undefined) {
		response.writeHead(404).end();
		return;
	}
	response.writeHead(200, { 'Content-Type': 'application/json' }).end(JSON.stringify(body));
}).listen(port);
