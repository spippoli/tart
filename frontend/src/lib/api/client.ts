import createClient, { type ClientOptions } from 'openapi-fetch';
import type { paths } from './schema';

/** A typed client for the TART API, generated from its OpenAPI schema (ADR 0004). */
export function createApiClient(options?: ClientOptions) {
	return createClient<paths>(options);
}
