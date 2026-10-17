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
 * `/api/contributions` keeps, for each User, one Submission of every status (see `contributions`).
 *
 * `GET /api/discovery/artworks` answers the Discovery query over thirty fictional
 * list entries made here (the backend's own tests cover the query): the Condition,
 * type, attribution, creation-year, and search filters, the title order, the `bbox` of
 * the Explore viewport, and pages of 24. They stand on ten fictional Locations, three
 * to each (`/api/discovery/locations` and `/api/discovery/locations/{id}`).
 * A session cookie of `archivio-vuoto` makes the archive empty.
 *
 * The contribution API keeps drafts of a new Artwork per User (`/api/contributions`):
 * start, read, autosave, submit, delete. A submit is refused as the real API would for a
 * missing document or initial Condition, a position outside the boundary, a note that
 * says `limite` (429), and terms not accepted (`…-accettati` addresses accepted them).
 * Uploads (`/api/media`) are `processing` for one poll, then `ready`; a file name with
 * `rifiutato` is refused, one with `gps` suggests the position of Location 200, and
 * `.pdf` is a PDF. The duplicate warning lists Location 200 for any point near it, and
 * the name rule finds the Artist `Nebbia Finta` for any name with `nebbia`.
 *
 *     node e2e/mock-api.ts [port]
 */
import { createHash, randomBytes } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';

const config = JSON.parse(readFileSync(new URL('fixtures/config.json', import.meta.url), 'utf8'));
const variants: Record<string, unknown> = {
	'/api/config': config,
	'/it-only/api/config': { ...config, languages: { ...config.languages, ui: ['it'] } },
	'/invite/api/config': { ...config, registration: 'invite' }
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

interface Invitation {
	id: number;
	email: string;
	status: 'pending' | 'used' | 'expired' | 'revoked';
	issuer: { number: number; display_name: string } | null;
	created_at: string;
	expires_at: string;
	used_at: string | null;
	revoked_at: string | null;
}
const DAY = 86_400_000;
const at = (days: number) => new Date(Date.now() + days * DAY).toISOString();
/** The Invitations of the `/invite` Instance, the latest first: one of each status but revoked. */
const invitationList: Invitation[] = [
	{
		id: 3,
		email: 'dal-terminale@example.org',
		status: 'pending',
		issuer: null,
		created_at: at(-2),
		expires_at: at(12),
		used_at: null,
		revoked_at: null
	},
	{
		id: 2,
		email: 'usata@example.org',
		status: 'used',
		issuer: { number: 7, display_name: 'Altra Moderatrice' },
		created_at: at(-5),
		expires_at: at(9),
		used_at: at(-3),
		revoked_at: null
	},
	{
		id: 1,
		email: 'scaduta@example.org',
		status: 'expired',
		issuer: { number: 7, display_name: 'Altra Moderatrice' },
		created_at: at(-20),
		expires_at: at(-6),
		used_at: null,
		revoked_at: null
	}
];

/** The Moderator API of Invitations: the real one has its own tests; this keeps a list. */
async function invitations(
	request: IncomingMessage,
	response: ServerResponse,
	path: string,
	inviteMode: boolean
) {
	const user = sessionUser(request);
	if (!user) return send(response, 401, { code: 'sign_in_required' });
	if (!user.moderator) return send(response, 403, { code: 'moderator_only' });
	if (!inviteMode) return send(response, 409, { code: 'registration_not_invite' });
	if (request.method === 'GET') return send(response, 200, { items: invitationList });
	if (!request.headers['x-tart-request'] || !request.headers['x-tart-client-ip']) {
		return send(response, 403, { code: 'csrf_refused' });
	}
	const revocation = /^\/api\/moderation\/invitations\/(\d+)\/revoke$/.exec(path);
	if (revocation) {
		const found = invitationList.find((each) => each.id === Number(revocation[1]));
		if (!found) return send(response, 404, { code: 'invitation_not_found' });
		if (found.status !== 'pending') return send(response, 409, { code: 'invitation_not_pending' });
		found.status = 'revoked';
		found.revoked_at = at(0);
		return send(response, 204);
	}
	const body = await readJson(request);
	const email = String(body.email ?? '')
		.trim()
		.toLowerCase();
	if (!/^[^@\s]+@[^@\s]+\.[^@\s.]+$/.test(email))
		return send(response, 400, { code: 'email_invalid' });
	if (invitationList.some((each) => each.email === email && each.status === 'pending')) {
		return send(response, 409, { code: 'invitation_pending' });
	}
	const created: Invitation = {
		id: Math.max(...invitationList.map((each) => each.id)) + 1,
		email,
		status: 'pending',
		issuer: { number: user.number, display_name: user.display_name },
		created_at: at(0),
		expires_at: at(14),
		used_at: null,
		revoked_at: null
	};
	invitationList.unshift(created);
	send(response, 201, created);
}

interface Draft {
	id: number;
	owner: string;
	status: 'draft' | 'submitted';
	workingCopy: unknown;
	lastAutosave: string | null;
	round: unknown;
}
const drafts = new Map<number, Draft>();
let nextDraftId = 500;
/** The Users who accepted the terms (the stand-in has one version); `…-accettati` from the start. */
const acceptedTerms = new Set<string>();
interface Upload {
	owner: string;
	name: string;
	polls: number;
}
const uploads = new Map<string, Upload>();
const PIXEL = Buffer.from(
	'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
	'base64'
);

function draftOut(draft: Draft) {
	return {
		id: draft.id,
		status: draft.status,
		target_kind: 'artwork',
		intent: 'create',
		target_id: null,
		base_revisions: [],
		labels: [],
		version: 1,
		submitter: { number: 1, display_name: 'Persona di prova' },
		created_at: at(0),
		first_submitted_at: draft.status === 'submitted' ? at(0) : null,
		rounds: draft.status === 'submitted' ? 1 : 0,
		last_round: draft.round ?? null,
		working_copy: draft.workingCopy ?? null,
		working_copy_discarded: false,
		last_autosave_at: draft.lastAutosave,
		outdated: [],
		expires_at: null,
		retry_of: null,
		converts: null,
		stub: false,
		log: []
	};
}

function termsOf(email: string) {
	const accepted = email.includes('accettati') || acceptedTerms.has(email);
	return { version: 1, accepted_version: accepted ? 1 : null, acceptance_required: !accepted };
}

/** The Location 200 and its three Artworks, as the duplicate warning lists them. */
function candidateAt(distance: number) {
	const panel = locationPanel(200, new URL('http://mock/'), false)!;
	return { location: panel.location, distance, site: null, artworks: panel.entries };
}

type Operation = {
	op?: string;
	kind?: string;
	record?: { geometry?: { coordinates?: unknown[] } };
};

/** The few rules of the real API's submit that the editor tests need, in its own codes. */
function refusalOf(content: { operations?: unknown; initial_condition?: unknown }): string | null {
	const operations: Operation[] = Array.isArray(content.operations) ? content.operations : [];
	const created = (kind: string) => operations.filter((o) => o.op === 'create' && o.kind === kind);
	if (created('documentation_item').length === 0) return 'moderation.documentation_required';
	if (!content.initial_condition) return 'moderation.initial_condition_required';
	const [place] = created('location');
	const coordinates = place?.record?.geometry?.coordinates;
	if (Array.isArray(coordinates) && Number(coordinates.flat(2)[0]) > 13) {
		return 'location.outside_boundary';
	}
	return null;
}

/** Drafts: started, read, autosaved, submitted, and deleted by their Submitter alone. */
async function editorDrafts(request: IncomingMessage, response: ServerResponse, path: string) {
	const email = sessionUser(request) && sessionEmail(request);
	if (!email) return send(response, 401, { code: 'sign_in_required' });
	const writes = request.method !== 'GET';
	if (writes && (!request.headers['x-tart-request'] || !request.headers['x-tart-client-ip'])) {
		return send(response, 403, { code: 'csrf_refused' });
	}
	if (path === '/api/contributions/terms') return send(response, 200, termsOf(email));
	if (path === '/api/contributions' && request.method === 'POST') {
		const draft: Draft = {
			id: nextDraftId++,
			owner: email,
			status: 'draft',
			workingCopy: null,
			lastAutosave: null,
			round: null
		};
		drafts.set(draft.id, draft);
		return send(response, 201, draftOut(draft));
	}
	const found = /^\/api\/contributions\/(\d+)(?:\/(working-copy|submit))?$/.exec(path);
	const draft = found && drafts.get(Number(found[1]));
	if (!found || !draft || draft.owner !== email) {
		return send(response, 404, { code: 'moderation.unknown_submission' });
	}
	if (request.method === 'GET') return send(response, 200, draftOut(draft));
	if (request.method === 'DELETE') {
		drafts.delete(draft.id);
		return send(response, 204);
	}
	const body = await readJson(request);
	if (found[2] === 'working-copy') {
		draft.workingCopy = body.content;
		draft.lastAutosave = at(0);
		return send(response, 200, { last_autosave_at: draft.lastAutosave });
	}
	if (found[2] === 'submit') {
		if (String(body.note ?? '').includes('limite')) {
			return send(response, 429, { code: 'moderation.submissions_limited', retry_after: 600 });
		}
		const refusal = refusalOf(body.content);
		if (refusal) return send(response, 422, { code: refusal });
		if (termsOf(email).acceptance_required && !body.accept_terms) {
			return send(response, 409, { code: 'moderation.terms_not_accepted' });
		}
		acceptedTerms.add(email);
		draft.status = 'submitted';
		draft.round = body.content;
		draft.workingCopy = null;
		return send(response, 200, draftOut(draft));
	}
	send(response, 404);
}

// Merge, Duplicate retirement, and Unmerge: the real API has its own tests; this keeps three
// drafts (ids 701 to 703, one of each kind, started by anyone) and starts copies of them.
const recordLink = (kind: string, id: number, name: string) => ({
	kind,
	id,
	path: `${id}-${name}`,
	name,
	location_title: null
});
const FOLDED = recordLink('artist', 2000, 'artista-doppio');
const SURVIVOR = recordLink('artist', 2001, 'artista-principale');
const MERGE_OPS = [
	{ op: 'add', target: 2001, collection: 'aliases', item: 'Artista Doppio' },
	{ op: 'merge', source: 2000, into: 2001 }
];
const UNMERGE_OPS = [
	{ op: 'remove', target: 2001, collection: 'aliases', key: 'Artista Doppio' },
	{ op: 'unmerge', source: 2000, into: 2001 }
];
const mergeDrafts = new Map<number, { intent: string; ops: unknown[]; status: string }>([
	[701, { intent: 'merge', ops: MERGE_OPS, status: 'draft' }],
	[
		702,
		{ intent: 'retirement', ops: [{ op: 'merge', source: 2100, into: 2101 }], status: 'draft' }
	],
	[703, { intent: 'unmerge', ops: UNMERGE_OPS, status: 'draft' }]
]);
let nextMergeId = 710;

function mergeReview(intent: string) {
	const retirement = intent === 'retirement';
	const source = retirement ? recordLink('documentation_item', 2100, 'foto-doppia') : FOLDED;
	const into = retirement ? recordLink('documentation_item', 2101, 'foto') : SURVIVOR;
	const alias = (item: string, origin: string) => ({
		collection: 'aliases',
		key: item,
		item,
		origin
	});
	return {
		intent,
		source,
		into,
		references: intent === 'merge' ? [recordLink('artwork', 2200, 'gatto')] : [],
		references_hidden: 0,
		items:
			intent === 'merge'
				? [alias('Artista Doppio', 'source'), alias('Artista Principale', 'into')]
				: [],
		fields:
			intent === 'merge'
				? [{ name: 'biography', source: 'Biografia di prova.', into: 'Altra biografia.' }]
				: [],
		contradictions: [],
		from_source: intent === 'unmerge' ? [alias('Artista Doppio', 'into')] : [],
		added_since: [],
		skipped: [],
		records: {}
	};
}

function mergeOut(id: number, draft: { intent: string; ops: unknown[]; status: string }) {
	const base = draftOut({
		id,
		owner: '',
		status: 'draft',
		workingCopy: { operations: draft.ops, initial_condition: null, conflicts: [] },
		lastAutosave: null,
		round: null
	});
	return {
		...base,
		status: draft.status,
		intent: draft.intent,
		target_kind: draft.intent === 'retirement' ? 'documentation_item' : 'artist',
		target_id: draft.intent === 'retirement' ? 2100 : 2000,
		base_revisions: [1, 1],
		last_round: draft.status === 'draft' ? null : { operations: draft.ops }
	};
}

async function merges(request: IncomingMessage, response: ServerResponse, path: string) {
	if (!sessionUser(request)) return send(response, 401, { code: 'sign_in_required' });
	if (request.method !== 'GET' && !request.headers['x-tart-request']) {
		return send(response, 403, { code: 'csrf_refused' });
	}
	const url = new URL(path, 'http://mock');
	if (url.pathname === '/api/contributions/merge-candidates') {
		const retirement = url.searchParams.get('source_id') === '2100';
		return send(response, 200, {
			source: retirement ? recordLink('documentation_item', 2100, 'foto-doppia') : FOLDED,
			items: retirement ? [] : [SURVIVOR]
		});
	}
	if (url.pathname === '/api/contributions/merge' && request.method === 'POST') {
		const body = await readJson(request);
		if (body.into_id === 9999)
			return send(response, 422, { code: 'moderation.merge_kind_mismatch' });
		const retirement = body.source_id === 2100;
		const id = nextMergeId++;
		mergeDrafts.set(id, {
			intent: retirement ? 'retirement' : 'merge',
			ops: retirement ? [{ op: 'merge', source: 2100, into: 2101 }] : MERGE_OPS,
			status: 'draft'
		});
		return send(response, 201, mergeOut(id, mergeDrafts.get(id)!));
	}
	const found = /^\/api\/contributions\/(\d+)(?:\/(merge|working-copy|submit))?$/.exec(
		url.pathname
	);
	const draft = found && mergeDrafts.get(Number(found[1]));
	if (!found || !draft) return send(response, 404, { code: 'moderation.unknown_submission' });
	const id = Number(found[1]);
	if (found[2] === 'merge') return send(response, 200, mergeReview(draft.intent));
	if (request.method === 'DELETE') {
		mergeDrafts.delete(id);
		return send(response, 204);
	}
	if (found[2] === 'working-copy') {
		const body = await readJson(request);
		draft.ops = body.content.operations;
		return send(response, 200, { last_autosave_at: at(0) });
	}
	if (found[2] === 'submit') {
		const body = await readJson(request);
		const twice =
			draft.intent === 'merge' &&
			JSON.stringify(body.content).includes('"collection":"aliases"') &&
			String(body.note ?? '').includes('rifiuta');
		if (twice) return send(response, 422, { code: 'artwork.creation_event_duplicated' });
		draft.status = 'submitted';
		draft.ops = body.content.operations;
		return send(response, 200, mergeOut(id, draft));
	}
	send(response, 200, mergeOut(id, draft));
}

/** Uploads: the file is `processing` for one poll, then `ready` (or refused if its name says so). */
async function media(request: IncomingMessage, response: ServerResponse, path: string) {
	const email = sessionUser(request) && sessionEmail(request);
	if (!email) return send(response, 401, { code: 'sign_in_required' });
	if (path === '/api/media' && request.method === 'POST') {
		if (!request.headers['x-tart-request'] || !request.headers['x-tart-client-ip']) {
			return send(response, 403, { code: 'csrf_refused' });
		}
		const chunks: Buffer[] = [];
		for await (const chunk of request) chunks.push(chunk as Buffer);
		const name = /filename="([^"]*)"/.exec(Buffer.concat(chunks).toString('latin1'))?.[1] ?? 'file';
		const hex = randomBytes(16).toString('hex');
		const id = `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
		uploads.set(id, { owner: email, name, polls: 0 });
		return send(response, 202, { id, status: 'processing' });
	}
	const state = /^\/api\/media\/([0-9a-f-]{36})(?:\/(thumbnail|view|large))?$/.exec(path);
	const upload = state && uploads.get(state[1]);
	if (!state || !upload) return send(response, 404, { code: 'upload_not_found' });
	if (state[2]) {
		response.writeHead(200, { 'Content-Type': 'image/png' }).end(PIXEL);
		return;
	}
	upload.polls += 1;
	if (upload.polls < 2) return send(response, 200, { id: state[1], status: 'processing' });
	if (upload.name.includes('rifiutato')) {
		return send(response, 200, {
			id: state[1],
			status: 'rejected',
			error: 'file_type_unsupported'
		});
	}
	send(response, 200, {
		id: state[1],
		status: 'ready',
		format: upload.name.endsWith('.pdf') ? 'pdf' : 'jpeg',
		renditions: { thumbnail: { width: 480, height: 320 } },
		suggestions: {
			observed_date: '2024-05-17',
			// The camera was at Location 200: a suggestion, never a Location.
			point: upload.name.includes('gps') ? [12.4823, 41.8955] : null
		}
	});
}

/** The duplicate warning's candidates: Location 200 is 12 m from any point near it. */
async function duplicates(request: IncomingMessage, response: ServerResponse, path: string) {
	if (!(sessionUser(request) && sessionEmail(request))) {
		return send(response, 401, { code: 'sign_in_required' });
	}
	const body = await readJson(request);
	if (path === '/api/contribution/duplicates/locations') {
		const [lon, lat] = body.geometry?.coordinates ?? [];
		const near = Math.abs(lon - 12.4823) < 0.001 && Math.abs(lat - 41.8955) < 0.001;
		return send(response, 200, {
			candidates: near || body.location_id === 200 ? [candidateAt(12)] : []
		});
	}
	const similar = String(body.name ?? '')
		.toLowerCase()
		.includes('nebbia');
	send(response, 200, {
		candidates:
			similar && body.kind === 'artist'
				? [
						{
							record: link('artist', 7, '7-nebbia-finta', 'Nebbia Finta'),
							match: 'name',
							matched: 'Nebbia Finta',
							score: 95
						}
					]
				: []
	});
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

/**
 * The contribution API (`/api/contributions`): the real one has its own tests; this keeps,
 * for each signed-in User, one Submission of every status (ids 101 to 106, and 107 an
 * Outdated one), as the Submitter reads them. A Moderator is never named to the
 * Submitter. Submission 200 belongs to someone else, so it answers 404.
 */
interface MockSubmission {
	id: number;
	status: string;
	target_kind: string;
	intent: 'create' | 'edit';
	target_id: number | null;
	labels: string[];
	outdated: string[];
	rounds: number;
	retry_of: number | null;
	log: Record<string, unknown>[];
	updated_at: string;
}

const submissionsOf = new Map<string, MockSubmission[]>();

function entry(
	event: string,
	days: number,
	actor: 'submitter' | 'moderator' | 'system',
	extra: Record<string, unknown> = {}
) {
	return {
		event,
		at: at(days),
		round: null,
		message: null,
		reason: null,
		related_submission: null,
		actor: { role: actor, user: null },
		...extra
	};
}

function seed(): MockSubmission[] {
	const submitted = entry('submitted', -3, 'submitter', { round: 1, message: 'Foto del 2021.' });
	const base = {
		target_kind: 'artwork',
		target_id: null,
		labels: [],
		outdated: [],
		retry_of: null
	};
	return [
		{
			...base,
			id: 101,
			status: 'draft',
			intent: 'create',
			rounds: 0,
			log: [],
			updated_at: at(-1)
		},
		{
			...base,
			id: 102,
			status: 'submitted',
			intent: 'create',
			labels: ['adds_documentation'],
			rounds: 1,
			log: [submitted],
			updated_at: at(-3)
		},
		{
			...base,
			id: 103,
			status: 'changes_requested',
			intent: 'create',
			rounds: 1,
			log: [
				submitted,
				entry('changes_requested', -2, 'moderator', {
					reason: 'duplicate',
					message: 'Sembra la stessa opera di una scheda esistente.'
				})
			],
			updated_at: at(-2)
		},
		{
			...base,
			id: 104,
			status: 'approved',
			intent: 'create',
			rounds: 1,
			log: [submitted, entry('approved', -1, 'moderator')],
			updated_at: at(-1)
		},
		{
			...base,
			id: 105,
			status: 'rejected',
			intent: 'create',
			rounds: 1,
			log: [
				submitted,
				entry('rejected', -1, 'moderator', {
					reason: 'duplicate',
					message: 'Esiste già una scheda per questo muro.'
				})
			],
			updated_at: at(-1)
		},
		{
			...base,
			id: 106,
			status: 'retracted',
			intent: 'create',
			rounds: 1,
			log: [submitted, entry('retracted', -1, 'submitter')],
			updated_at: at(-1)
		},
		{
			...base,
			id: 107,
			status: 'submitted',
			intent: 'edit',
			target_id: 42,
			outdated: ['field_changed'],
			rounds: 1,
			log: [submitted],
			updated_at: at(-4)
		}
	];
}

let nextSubmissionId = 300;

function detail(item: MockSubmission, number: number, name: string) {
	return {
		id: item.id,
		status: item.status,
		target_kind: item.target_kind,
		intent: item.intent,
		target_id: item.target_id,
		base_revisions: [],
		labels: item.labels,
		version: 1,
		submitter: { number, display_name: name },
		created_at: at(-5),
		first_submitted_at: item.rounds > 0 ? at(-3) : null,
		rounds: item.rounds,
		last_round:
			item.rounds > 0
				? {
						operations: [
							{
								op: 'create',
								ref: 'a',
								kind: 'artwork',
								record: { title: 'Mercato di prova (opera fittizia)' }
							}
						]
					}
				: null,
		working_copy: null,
		working_copy_discarded: false,
		last_autosave_at: null,
		outdated: item.outdated,
		expires_at: item.status === 'changes_requested' ? at(28) : null,
		retry_of: item.retry_of,
		converts: null,
		stub: false,
		log: item.log
	};
}

async function contributions(
	request: IncomingMessage,
	response: ServerResponse,
	path: string
): Promise<void> {
	const user = sessionUser(request);
	const email = sessionEmail(request);
	if (!user || !email) return send(response, 401, { code: 'sign_in_required' });
	if (request.method !== 'GET') {
		if (!request.headers['x-tart-request'] || !request.headers['x-tart-client-ip']) {
			return send(response, 403, { code: 'csrf_refused' });
		}
	}
	const mine = submissionsOf.get(email) ?? (email.startsWith('persona-vuota') ? [] : seed());
	submissionsOf.set(email, mine);
	const url = new URL(path, 'http://mock');
	const summary = (each: MockSubmission) => ({
		id: each.id,
		status: each.status,
		target_kind: each.target_kind,
		intent: each.intent,
		target_id: each.target_id,
		labels: each.labels,
		created_at: at(-5),
		updated_at: each.updated_at,
		expires_at: each.status === 'changes_requested' ? at(28) : null
	});
	if (url.pathname === '/api/contributions' && request.method === 'GET') {
		const status = url.searchParams.get('status');
		const items = mine.filter((each) => !status || each.status === status);
		return send(response, 200, { items: items.map(summary) });
	}
	if (url.pathname === '/api/contributions' && request.method === 'POST') {
		const created: MockSubmission = {
			...seed()[0],
			id: nextSubmissionId++
		};
		mine.unshift(created);
		return send(response, 201, detail(created, user.number, user.display_name));
	}
	const found = /^\/api\/contributions\/(\d+)(?:\/([a-z-]+))?$/.exec(url.pathname);
	if (!found) return send(response, 404);
	const item = mine.find((each) => each.id === Number(found[1]));
	if (!item) return send(response, 404, { code: 'moderation.unknown_submission' });
	const action = found[2];
	const open = item.status === 'submitted' || item.status === 'changes_requested';
	if (request.method === 'GET')
		return send(response, 200, detail(item, user.number, user.display_name));
	if (request.method === 'DELETE') {
		if (item.status !== 'draft')
			return send(response, 409, { code: 'moderation.invalid_transition' });
		mine.splice(mine.indexOf(item), 1);
		return send(response, 204);
	}
	if (action === 'retract') {
		if (!open) return send(response, 409, { code: 'moderation.invalid_transition' });
		item.status = 'retracted';
		item.log.push(entry('retracted', 0, 'submitter'));
		return send(response, 200, detail(item, user.number, user.display_name));
	}
	if (action === 'start-again') {
		if (item.status !== 'rejected' && item.status !== 'retracted') {
			return send(response, 409, { code: 'moderation.cannot_start_again' });
		}
		const created: MockSubmission = { ...seed()[0], id: nextSubmissionId++, retry_of: item.id };
		mine.unshift(created);
		return send(response, 201, detail(created, user.number, user.display_name));
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

const CONDITION_CYCLE: [string, string][] = [
	['intact', 'present'],
	['covered', 'disappeared'],
	['destroyed', 'disappeared'],
	['unknown', 'unknown'],
	['damaged', 'present']
];
const yearDate = (year: number) => ({
	precision: 'year',
	qualifier: 'exact',
	first: `${year}-01-01`,
	second: null
});
const link = (kind: string, id: number, path: string, name: string) => ({
	kind,
	id,
	path,
	name,
	location_title: null
});

/** Ten fictional Locations of three Artworks each, about 300 m apart, around the default view. */
const locationPoint = (id: number): [number, number] => [
	12.4823 + ((id - 200) % 5) * 0.0035,
	41.8955 + Math.floor((id - 200) / 5) * 0.004
];

/** Thirty fictional list entries: ten have no creation date, one has no documentation. */
const entries = Array.from({ length: 30 }, (_, index) => {
	const [condition, group] = CONDITION_CYCLE[index % CONDITION_CYCLE.length];
	const undocumented = index === 2;
	return {
		id: 100 + index,
		path: `${100 + index}-opera-di-prova-${index + 1}`,
		title: index === 29 ? null : `Opera di prova ${String(index + 1).padStart(2, '0')}`,
		expression_types: index % 2 ? ['mural'] : ['stencil'],
		creationYear: index < 10 ? null : 2000 + index,
		attribution: index % 4 === 0 ? 'attributed' : index % 4 === 1 ? 'disputed' : 'unknown',
		condition: {
			condition,
			group,
			since: yearDate(2019),
			evidence_level: 'reported',
			event: null
		},
		last_documented: undocumented ? null : yearDate(2020 + (index % 5)),
		location: 200 + Math.floor(index / 3),
		location_point: locationPoint(200 + Math.floor(index / 3)),
		site: index % 3 === 0 ? link('site', 5, '5-deposito', 'Deposito fittizio') : null,
		area: link('area', 3, '3-quartiere-immaginario', 'Quartiere Immaginario'),
		approximate: index % 7 === 0,
		attributed:
			index % 4 === 0 ? [link('artist', 7, '7-nebbia-finta', 'Nebbia Finta')] : ([] as unknown[]),
		disputed:
			index % 4 === 1
				? [link('artist', 8, '8-collettivo-vernice-assente', 'Collettivo Vernice Assente')]
				: ([] as unknown[]),
		// On the second page, which the map tests never load: the stand-in serves no media.
		probable: index % 8 === 0 ? [7] : ([] as unknown[]),
		thumbnail:
			index === 27
				? {
						id: 300,
						path: '300',
						medium: 'image',
						observed_date: yearDate(2021),
						file: 'fictional/photo',
						renditions: { view: { width: 400, height: 300 } },
						alt_text: 'Una fotografia fittizia di un muro dipinto.'
					}
				: null,
		latest_item_medium: undocumented ? null : index % 5 === 0 ? 'link' : 'text'
	};
});

/** The entries that the filters of a query select, in the API's own parameters (no page or box). */
function matchingEntries(query: URLSearchParams, emptyArchive: boolean) {
	const list = (name: string) => query.getAll(name);
	const number = (name: string) => (query.get(name) === null ? null : Number(query.get(name)));
	const text = query.get('q')?.trim().toLowerCase() ?? '';
	let matching = emptyArchive ? [] : entries;
	if (text.length >= 2) {
		matching = matching.filter((entry) =>
			(entry.title ?? 'senza titolo').toLowerCase().includes(text)
		);
	}
	if (list('condition').length) {
		matching = matching.filter((entry) => list('condition').includes(entry.condition.condition));
	}
	if (list('type').length) {
		matching = matching.filter((entry) =>
			entry.expression_types.some((type) => list('type').includes(type))
		);
	}
	if (list('attribution').length) {
		matching = matching.filter((entry) => list('attribution').includes(entry.attribution));
	}
	const [from, to] = [number('created_from'), number('created_to')];
	const dated = from !== null || to !== null;
	const leftOut = dated ? matching.filter((entry) => entry.creationYear === null).length : 0;
	if (dated) {
		matching = matching.filter(
			(entry) =>
				entry.creationYear !== null &&
				(from === null || entry.creationYear >= from) &&
				(to === null || entry.creationYear <= to)
		);
	}
	if (query.get('order') === 'title') {
		matching = [...matching].sort((a, b) => (a.title ?? '￿').localeCompare(b.title ?? '￿'));
	}
	return { matching, leftOut, text };
}

/** What the API does not send: the fixture's own bookkeeping. */
function shownEntry(entry: (typeof entries)[number]) {
	const shown: Record<string, unknown> = { ...entry };
	delete shown.creationYear;
	delete shown.attribution;
	return shown;
}

function discovery(url: URL, emptyArchive: boolean) {
	const query = url.searchParams;
	const { leftOut, text, ...found } = matchingEntries(query, emptyArchive);
	let { matching } = found;
	// `bbox`: west, south, east, north; only Locations whose sign lies inside.
	const box = query.get('bbox')?.split(',').map(Number);
	if (box) {
		matching = matching.filter(({ location_point: [lon, lat] }) => {
			return lon >= box[0] && lat >= box[1] && lon <= box[2] && lat <= box[3];
		});
	}
	const page = Number(query.get('page') ?? '1');
	const shown = matching.slice((page - 1) * 24, page * 24);
	return {
		entries: shown.map(shownEntry),
		total: matching.length,
		page,
		page_size: 24,
		also_matching: text.includes('nebbia')
			? {
					kinds: [
						{
							kind: 'artist',
							items: [
								{ record: link('artist', 7, '7-nebbia-finta', 'Nebbia Finta'), alias: 'Nebbia' }
							],
							total: 4
						}
					]
				}
			: null,
		left_out: leftOut
	};
}

const GROUPS = ['present', 'unknown', 'disappeared'] as const;

/** `GET /api/discovery/locations`: one feature per Location with a matching Artwork. */
function mapLocations(url: URL, emptyArchive: boolean) {
	const { matching } = matchingEntries(url.searchParams, emptyArchive);
	const byLocation = new Map<number, typeof matching>();
	for (const entry of matching) {
		byLocation.set(entry.location, [...(byLocation.get(entry.location) ?? []), entry]);
	}
	const features = [...byLocation].map(([id, found]) => {
		const counts = Object.fromEntries(
			GROUPS.map((group) => [
				group,
				found.filter((entry) => entry.condition.group === group).length
			])
		);
		const point = locationPoint(id);
		return {
			type: 'Feature',
			geometry: { type: 'Point', coordinates: point },
			properties: {
				id,
				...counts,
				group: GROUPS.find((group) => counts[group] > 0),
				count: found.length,
				point,
				approximate: false,
				radius: null
			}
		};
	});
	return {
		type: 'FeatureCollection',
		features,
		sites: [],
		areas: [{ name: 'Quartiere Immaginario', point: [12.4923, 41.9] }]
	};
}

/** `GET /api/discovery/locations/{id}`: the header and the stratigraphy, or none. */
function locationPanel(id: number, url: URL, emptyArchive: boolean) {
	const here = entries.filter((entry) => entry.location === id);
	if (here.length === 0) return null;
	const found = new Set(matchingEntries(url.searchParams, emptyArchive).matching.map((e) => e.id));
	const shown = here.filter((entry) => found.has(entry.id));
	const point = locationPoint(id);
	return {
		location: {
			id,
			path: `${id}-superficie-di-prova`,
			title: { place_description: `Parete di prova ${id - 199}`, surface_type: null, place: null },
			surface_type: 'building_wall',
			geometry: { type: 'Point', coordinates: point },
			point,
			// The first Location is approximate with a radius, the second without.
			approximate: id === 200 || id === 201,
			uncertainty_radius: id === 200 ? 30 : null
		},
		site: null,
		areas: [link('area', 3, '3-quartiere-immaginario', 'Quartiere Immaginario')],
		// Most recent first; with none matching, all of them.
		entries: (shown.length > 0 ? shown : here).reverse().map(shownEntry),
		matches: shown.length > 0,
		other: shown.length > 0 ? here.length - shown.length : 0
	};
}

const port = Number(process.argv[2] ?? 8795);
createServer((request, response) => {
	const path = (request.url ?? '').replace(/^\/(it-only|invite)/, '');
	if (path.startsWith('/api/moderation/invitations')) {
		invitations(request, response, path, (request.url ?? '').startsWith('/invite/')).catch(() =>
			send(response, 500)
		);
		return;
	}
	if (
		/^\/api\/contributions\/(merge|unmerge|merge-candidates)/.test(path) ||
		/^\/api\/contributions\/(7\d\d|7\d\d\/.*)$/.test(path)
	) {
		merges(request, response, path).catch(() => send(response, 500));
		return;
	}
	if (path.startsWith('/api/contributions')) {
		// The editor's drafts (ids from 500, started with the editor header) and the terms are
		// kept by `editorDrafts`; the Submissions of the hub and My contributions by `contributions`.
		const id = Number(/^\/api\/contributions\/(\d+)/.exec(path)?.[1] ?? 0);
		const editor =
			path === '/api/contributions/terms' ||
			id >= 500 ||
			(path === '/api/contributions' && request.headers['x-mock-editor'] !== undefined);
		(editor ? editorDrafts : contributions)(request, response, path).catch(() =>
			send(response, 500)
		);
		return;
	}
	if (path.startsWith('/api/media')) {
		media(request, response, path).catch(() => send(response, 500));
		return;
	}
	if (path.startsWith('/api/contribution/duplicates/')) {
		duplicates(request, response, path).catch(() => send(response, 500));
		return;
	}
	if (path.startsWith('/api/auth/')) {
		auth(request, response, path).catch(() => send(response, 500));
		return;
	}
	if (path.startsWith('/api/archive/')) {
		archive(request, response, path);
		return;
	}
	if (path.startsWith('/api/discovery/')) {
		const empty = sessionEmail(request)?.startsWith('archivio-vuoto') ?? false;
		const url = new URL(path, 'http://mock');
		if (url.pathname === '/api/discovery/artworks')
			return send(response, 200, discovery(url, empty));
		if (url.pathname === '/api/discovery/locations')
			return send(response, 200, mapLocations(url, empty));
		const id = /^\/api\/discovery\/locations\/(\d+)$/.exec(url.pathname)?.[1];
		const panel = id && locationPanel(Number(id), url, empty);
		return panel
			? send(response, 200, panel)
			: send(response, 404, { code: 'location_not_available' });
	}
	const body = variants[request.url ?? ''];
	if (request.method !== 'GET' || body === undefined) {
		response.writeHead(404).end();
		return;
	}
	response.writeHead(200, { 'Content-Type': 'application/json' }).end(JSON.stringify(body));
}).listen(port);
