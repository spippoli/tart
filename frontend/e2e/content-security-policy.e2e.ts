import { expect, test } from '@playwright/test';

// Discovery criterion 48: the stand-in API's map styles load tiles from an external
// https origin, which every page's Content-Security-Policy allows.
test('AC 48: an external tile origin is in the Content-Security-Policy', async ({ request }) => {
	const response = await request.get('/it/informazioni');

	expect(response.status()).toBe(200);
	expect(response.headers()['content-security-policy']).toBe(
		"connect-src 'self' https://tiles.example.org"
	);
});
