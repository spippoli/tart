/**
 * The editor's calls to the API, made by the browser (Foundations spec, Upload path:
 * uploads never pass through SvelteKit; Caddy sends `/api/*` to the API, which reads the
 * session cookie and requires the CSRF header). Each call answers with the outcome as a
 * value, never an exception: the form shows a failure beside the action and keeps the
 * draft.
 */
import { createApiClient } from '../api/client';
import type { components } from '../api/schema';
import type { Geometry } from '#lib/map/drawing.ts';

type Schemas = components['schemas'];
export type Submission = Schemas['SubmissionOut'];

/** What a successful call answers, as the client types it. */
type Value<F extends (...args: never[]) => Promise<Outcome<unknown>>> = Extract<
	Awaited<ReturnType<F>>,
	{ ok: true }
>['value'];
export type UploadState = Value<typeof uploadState>;
export type LocationCandidate = Value<typeof locationCandidates>['candidates'][number];
export type NameCandidate = Value<typeof nameCandidates>['candidates'][number];
export type RecordLink = Value<typeof searchRecords>['items'][number];

/** A refusal: the stable error code, the status, and the wait of a rate limit. */
export interface Failure {
	code: string;
	status: number;
	/** Seconds until the action is possible again (429). */
	retryAfter?: number;
}

export type Outcome<T> = { ok: true; value: T } | { ok: false; failure: Failure };

const client = createApiClient();

function failure(response: Response, body: unknown): Outcome<never> {
	const detail = typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
	return {
		ok: false,
		failure: {
			code: typeof detail.code === 'string' ? detail.code : 'unknown',
			status: response.status,
			retryAfter: typeof detail.retry_after === 'number' ? detail.retry_after : undefined
		}
	};
}

/** A network failure: the request did not reach the API. */
const OFFLINE: Outcome<never> = { ok: false, failure: { code: 'network', status: 0 } };

async function attempt<T>(
	call: () => Promise<{ data?: T; error?: unknown; response: Response }>
): Promise<Outcome<T>> {
	try {
		const { data, error, response } = await call();
		return data !== undefined && response.ok ? { ok: true, value: data } : failure(response, error);
	} catch {
		return OFFLINE;
	}
}

export function autosave(id: number, content: Record<string, unknown>) {
	return attempt(() =>
		client.PUT('/api/contributions/{submission_id}/working-copy', {
			params: { path: { submission_id: id } },
			body: { content }
		})
	);
}

export function submit(
	id: number,
	content: Record<string, unknown>,
	note: string,
	acceptTerms: boolean
) {
	return attempt(() =>
		client.POST('/api/contributions/{submission_id}/submit', {
			params: { path: { submission_id: id } },
			body: { content, note: note.trim() || null, accept_terms: acceptTerms }
		})
	);
}

/** Start a Merge, or a Duplicate retirement, of the first record into the second. */
export function startMerge(sourceId: number, intoId: number) {
	return attempt(() =>
		client.POST('/api/contributions/merge', { body: { source_id: sourceId, into_id: intoId } })
	);
}

export async function deleteDraft(id: number): Promise<Outcome<null>> {
	try {
		const { error, response } = await client.DELETE('/api/contributions/{submission_id}', {
			params: { path: { submission_id: id } }
		});
		return response.ok ? { ok: true, value: null } : failure(response, error);
	} catch {
		return OFFLINE;
	}
}

/** Upload one file; the API answers 202 and processes it in the background. */
export async function uploadFile(file: File): Promise<Outcome<UploadState>> {
	const body = new FormData();
	body.set('file', file);
	try {
		const response = await fetch('/api/media', {
			method: 'POST',
			body,
			headers: { 'X-TART-Request': '1' }
		});
		const json: unknown = await response.json().catch(() => ({}));
		return response.ok ? { ok: true, value: json as UploadState } : failure(response, json);
	} catch {
		return OFFLINE;
	}
}

export function uploadState(id: string) {
	return attempt(() =>
		client.GET('/api/media/{upload_id}', { params: { path: { upload_id: id } } })
	);
}

/** Locations within the proximity rule of a place just chosen, or of a Location chosen. */
export function locationCandidates(
	place: { geometry: Geometry; radius: number | null } | { locationId: number }
) {
	return attempt(() =>
		client.POST('/api/contribution/duplicates/locations', {
			body:
				'locationId' in place
					? { location_id: place.locationId }
					: {
							geometry: place.geometry as unknown as { [key: string]: unknown },
							uncertainty_radius: place.radius
						}
		})
	);
}

export function nameCandidates(
	kind: 'artist' | 'site' | 'series' | 'area' | 'source',
	name: string,
	url?: string
) {
	return attempt(() =>
		client.POST('/api/contribution/duplicates/names', {
			body: { kind, name, url: url?.trim() || null }
		})
	);
}

/** The public Artists or Series whose name matches, by name. */
export function searchRecords(kind: 'artists' | 'series', name: string) {
	return attempt(() =>
		client.GET(kind === 'artists' ? '/api/archive/artists' : '/api/archive/series', {
			params: { query: { name } }
		})
	);
}

/** The Artworks matching a text, whose Locations an Artwork may be put on. */
export function searchArtworks(text: string) {
	return attempt(() => client.GET('/api/discovery/artworks', { params: { query: { q: text } } }));
}
