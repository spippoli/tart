import type { RequestEvent } from '@sveltejs/kit';
import { describe, expect, it } from 'vitest';
import {
	contentSecurityPolicy,
	createContentSecurityPolicyHandle
} from './content-security-policy';

async function policyOf(readConfig: () => Promise<{ map_tile_origins: string[] }>) {
	const handle = createContentSecurityPolicyHandle(readConfig);
	const response = await handle({
		event: {} as RequestEvent,
		resolve: async () =>
			new Response('<!doctype html>', { headers: { 'Content-Type': 'text/html' } })
	});
	return response.headers.get('Content-Security-Policy');
}

// Discovery criterion 48: an external https tile origin is added to the Content-Security-Policy.
describe('the Content-Security-Policy', () => {
	it('adds the external tile origins of the map styles', async () => {
		const policy = await policyOf(async () => ({
			map_tile_origins: ['https://raster.example.net:8443', 'https://tiles.example.org']
		}));

		expect(policy).toBe(
			"connect-src 'self' https://raster.example.net:8443 https://tiles.example.org"
		);
	});

	it('allows only the own origin with the local basemap', () => {
		expect(contentSecurityPolicy([])).toBe("connect-src 'self'");
	});

	it('allows only the own origin when the configuration cannot be read', async () => {
		const policy = await policyOf(() => Promise.reject(new Error('GET /api/config answered 503')));

		expect(policy).toBe("connect-src 'self'");
	});
});
