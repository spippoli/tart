/**
 * A stand-in for the `api` service in the end-to-end tests: it answers
 * `GET /api/config` with a fictional public configuration. Under the `/it-only`
 * prefix, the same configuration enables Italian alone, for a second frontend
 * server that tests a disabled UI language.
 *
 * It also stands in for sign-in (`/api/auth/*`), with fixed rules instead of the
 * API's: every code is `123456`; `persona@…` and `moderatrice@…` (the Moderator)
 * are Users from the start, any other address registers; `limitata@…` is rate
 * limited; the session token is the address the User first signed in with, which
 * keeps naming them after an email change. An email change also takes `123456`;
 * `presa@…` addresses are in use. It refuses a state-changing request
 * without the CSRF header or the client IP, as the API would not know the IP.
 * Passkeys are kept by credential id and checked for nothing else: the browser's
 * virtual authenticator makes them, and the API's own tests verify them.
 *
 * The archive (`/api/archive/*`) answers with the real API's responses over the
 * fictional dataset, in `fixtures/archive` (written by the backend's
 * `test_archive_e2e_fixtures.py`): a Moderator gets the `moderator/` variant where there
 * is one, everyone the `redacted/` one. Id 9001 is a withdrawn record (410) and 9002 an
 * Artwork merged into the complete record (301).
 *
 *     node e2e/mock-api.ts [port]
 */
import { createHash, randomBytes } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';

const config = JSON.parse(readFileSync(new URL('fixtures/config.json', import.meta.url), 'utf8'));
const variants: Record<string, unknown> = {
	'/api/config': config,
	'/it-only/api/config': { ...config, languages: { ...config.languages, ui: ['it'] } }
};

const CODE = '123456';
interface User {
	email: string;
	display_name: string;
	moderator: boolean;
	language: string;
}
const users = new Map<string, User>();
/** Sessions ended by Sign out everywhere, until the next sign-in. */
const revoked = new Set<string>();
const pendingEmail = new Map<string, string>();

/** The session token of the User with this address, if there is one. */
function userKey(email: string): string | null {
	for (const [key, user] of users) if (user.email === email) return key;
	return users.has(email) ? null : isPreset(email) ? email : null;
}

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
	if (!email || revoked.has(email)) return null;
	if (!users.has(email) && isPreset(email)) {
		users.set(email, {
			email,
			display_name: email.startsWith('moderatrice') ? 'Moderatrice di prova' : 'Persona di prova',
			moderator: email.startsWith('moderatrice'),
			language: 'it'
		});
	}
	const user = users.get(email);
	return user
		? {
				number: 1,
				display_name: user.display_name,
				preferred_language: user.language,
				moderator: user.moderator
			}
		: null;
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

function signedIn(key: string) {
	revoked.delete(key);
	return {
		'Set-Cookie': `tart_session=${encodeURIComponent(key)}; HttpOnly; Max-Age=7776000; Path=/; SameSite=lax; Secure`
	};
}

function displayNameProblem(value: unknown): string | null {
	const name = String(value).trim();
	if (name.length < 1 || name.length > 40) return 'display_name_length';
	if (/^(deleted user|utente eliminato) \d+$/i.test(name)) return 'display_name_reserved';
	return null;
}

async function auth(request: IncomingMessage, response: ServerResponse, path: string) {
	if (path === '/api/auth/session' && request.method === 'GET') {
		return send(response, 200, { user: sessionUser(request) });
	}
	if (path.startsWith('/api/auth/account')) return account(request, response, path);
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
	if (path === '/api/auth/sign-out-everywhere') {
		const key = sessionUser(request) && sessionEmail(request);
		if (!key) return send(response, 401, { code: 'sign_in_required' });
		revoked.add(key);
		return send(response, 204);
	}
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
		const key = userKey(email);
		if (key) return send(response, 200, { outcome: 'signed_in' }, signedIn(key));
		const registration = body.registration;
		if (!registration) return send(response, 200, { outcome: 'registration_required' });
		if (!registration.age_confirmed) return send(response, 400, { code: 'age_not_confirmed' });
		const problem = displayNameProblem(registration.display_name);
		if (problem) return send(response, 400, { code: problem });
		users.set(email, {
			email,
			display_name: String(registration.display_name).trim(),
			moderator: false,
			language: body.language
		});
		return send(response, 200, { outcome: 'signed_in' }, signedIn(email));
	}
	send(response, 404);
}

async function account(request: IncomingMessage, response: ServerResponse, path: string) {
	const key = sessionUser(request) && sessionEmail(request);
	if (!key) return send(response, 401, { code: 'sign_in_required' });
	const user = users.get(key)!;
	const state = () => ({
		number: 1,
		email: user.email,
		display_name: user.display_name,
		preferred_language: user.language
	});
	if (request.method === 'GET') return send(response, 200, state());
	if (!request.headers['x-tart-request'] || !request.headers['x-tart-client-ip']) {
		return send(response, 403, { code: 'csrf_refused' });
	}
	const body = await readJson(request);
	if (path === '/api/auth/account' && request.method === 'PATCH') {
		if (body.display_name !== undefined) {
			const problem = displayNameProblem(body.display_name);
			if (problem) return send(response, 400, { code: problem });
			user.display_name = String(body.display_name).trim();
		}
		if (body.preferred_language !== undefined) {
			if (!['it', 'en'].includes(body.preferred_language)) {
				return send(response, 400, { code: 'language_unavailable' });
			}
			user.language = body.preferred_language;
		}
		return send(response, 200, state());
	}
	if (path === '/api/auth/account/email') {
		const email = String(body.email ?? '')
			.trim()
			.toLowerCase();
		if (!email.includes('@')) return send(response, 400, { code: 'email_invalid' });
		if (email === user.email) return send(response, 400, { code: 'email_unchanged' });
		if (email.startsWith('presa') || userKey(email)) pendingEmail.delete(key);
		else pendingEmail.set(key, email);
		return send(response, 202, {});
	}
	if (path === '/api/auth/account/email/verify') {
		const email = pendingEmail.get(key);
		if (body.code !== CODE || !email) return send(response, 400, { code: 'code_invalid' });
		pendingEmail.delete(key);
		user.email = email;
		return send(response, 200, state());
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

const ARCHIVE = new URL('fixtures/archive/', import.meta.url);
export const WITHDRAWN_ID = 9001;
export const MERGED_ID = 9002;

// Records the fictional dataset has no case for (a Location with neighbours within
// 500 m, a Series with no visible Location), written by hand.
const EXTRA = new URL('fixtures/archive-extra/', import.meta.url);

function archiveFile(name: string): unknown {
	for (const directory of [ARCHIVE, EXTRA]) {
		const file = new URL(name, directory);
		if (existsSync(file)) return JSON.parse(readFileSync(file, 'utf8'));
	}
	return undefined;
}

const fold = (text: string) => text.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();

/** The index by name: a stand-in for the API's name matching, which its own tests cover. */
function filtered(index: { items: { name: string | null }[] }, name: string | null) {
	if (!name) return index;
	const items = index.items.filter((item) => fold(item.name ?? '').includes(fold(name)));
	return { ...index, items, total: items.length };
}

function archive(request: IncomingMessage, response: ServerResponse, url: string) {
	const [path, query] = url.slice('/api/archive/'.length).split('?');
	const [segment, id, revisions] = path.split('/');
	if (Number(id) === WITHDRAWN_ID) return send(response, 410, { code: 'record_withdrawn' });
	if (Number(id) === MERGED_ID && segment === 'artworks') {
		const ids = archiveFile('ids.json') as Record<string, number>;
		return send(response, 301, undefined, {
			Location: `/api/archive/artworks/${ids.gatto}${revisions ? '/revisions' : ''}`
		});
	}
	const name =
		id === undefined
			? `${segment}/index.json`
			: `${segment}/${id}${revisions ? '.revisions' : ''}.json`;
	const body =
		(sessionUser(request)?.moderator ? archiveFile(`moderator/${name}`) : undefined) ??
		archiveFile(`redacted/${name}`) ??
		archiveFile(name);
	if (body === undefined) return send(response, 404, { code: 'record_not_found' });
	send(
		response,
		200,
		id === undefined
			? filtered(
					body as { items: { name: string | null }[] },
					new URLSearchParams(query).get('name')
				)
			: body
	);
}

const port = Number(process.argv[2] ?? 8795);
createServer((request, response) => {
	const path = (request.url ?? '').replace(/^\/it-only/, '');
	if (path.startsWith('/api/auth/')) {
		auth(request, response, path).catch(() => send(response, 500));
		return;
	}
	if (path.startsWith('/api/archive/')) {
		archive(request, response, path);
		return;
	}
	const body = variants[request.url ?? ''];
	if (request.method !== 'GET' || body === undefined) {
		response.writeHead(404).end();
		return;
	}
	response.writeHead(200, { 'Content-Type': 'application/json' }).end(JSON.stringify(body));
}).listen(port);
