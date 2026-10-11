import createClient, { type ClientOptions } from 'openapi-fetch';
import type { paths } from './schema';

/**
 * The custom header the API requires on every state-changing request (ADR 0005,
 * CSRF); a cross-site page cannot send it.
 */
export const CSRF_HEADER = 'X-TART-Request';

/** A typed client for the TART API, generated from its OpenAPI schema (ADR 0004). */
export function createApiClient(options?: ClientOptions) {
	return createClient<paths>({ ...options, headers: { [CSRF_HEADER]: '1', ...options?.headers } });
}
