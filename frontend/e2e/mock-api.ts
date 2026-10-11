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
 *
 *     node e2e/mock-api.ts [port]
 */
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

function sessionUser(request: IncomingMessage) {
	const token = /(?:^|;\s*)tart_session=([^;]+)/.exec(request.headers.cookie ?? '')?.[1];
	if (!token) return null;
	const email = decodeURIComponent(token);
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
	if (
		request.method !== 'POST' ||
		!request.headers['x-tart-request'] ||
		!request.headers['x-tart-client-ip']
	) {
		return send(response, 403, { code: 'csrf_refused' });
	}
	if (path === '/api/auth/sign-out') return send(response, 204, undefined, signedIn(''));
	const body = await readJson(request);
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
