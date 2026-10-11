import { expect, it } from 'vitest';
import { createApiClient } from './client';

it('calls the API paths of the schema', async () => {
	const requested: string[] = [];
	const client = createApiClient({
		baseUrl: 'https://archive.example',
		fetch: async (request: Request) => {
			requested.push(request.url);
			return new Response('ok', { headers: { 'Content-Type': 'text/plain' } });
		}
	});

	const { data } = await client.GET('/api/health', { parseAs: 'text' });

	expect(requested).toEqual(['https://archive.example/api/health']);
	expect(data).toBe('ok');
});
