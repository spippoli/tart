import { describe, expect, it } from 'vitest';
import { createApiClient } from '../api/client';
import { CACHE_MILLISECONDS, createInstanceConfigReader } from './instance-config';

// Foundations criterion 8: the frontend reads configuration only through the API endpoint.
describe('the Instance configuration reader', () => {
	function apiAnswering(status: number) {
		const requested: string[] = [];
		const client = createApiClient({
			baseUrl: 'http://api:8000',
			fetch: async (request: Request) => {
				requested.push(request.url);
				return new Response(JSON.stringify({ terms_version: requested.length }), {
					status,
					headers: { 'Content-Type': 'application/json' }
				});
			}
		});
		return { client, requested };
	}

	it('reads GET /api/config once and caches it', async () => {
		const { client, requested } = apiAnswering(200);
		const read = createInstanceConfigReader(client, () => 0);

		const first = await read();
		const second = await read();

		expect(requested).toEqual(['http://api:8000/api/config']);
		expect(second).toBe(first);
	});

	it('reads it again once the cache has expired', async () => {
		const { client, requested } = apiAnswering(200);
		let clock = 0;
		const read = createInstanceConfigReader(client, () => clock);

		await read();
		clock = CACHE_MILLISECONDS;
		const reread = await read();

		expect(requested).toHaveLength(2);
		expect(reread.terms_version).toBe(2);
	});

	it('does not cache a failed read', async () => {
		const { client, requested } = apiAnswering(503);
		const read = createInstanceConfigReader(client, () => 0);

		await expect(read()).rejects.toThrow('GET /api/config answered 503');
		await expect(read()).rejects.toThrow();
		expect(requested).toHaveLength(2);
	});
});
