import type { Cookies } from '@sveltejs/kit';
import { describe, expect, it } from 'vitest';
import { relaySessionCookie } from './session-cookie';

function recordingCookies() {
	const set: [string, string, object][] = [];
	return { set, cookies: { set: (...args: [string, string, object]) => set.push(args) } };
}

// Foundations criterion 13: the browser gets the API's session cookie, HttpOnly and SameSite=Lax.
describe('relaying the session cookie', () => {
	it('passes the session on with its lifetime', () => {
		const { set, cookies } = recordingCookies();
		const response = new Response(null, {
			headers: [
				['set-cookie', 'other=1; Path=/'],
				[
					'set-cookie',
					'tart_session=abc-123; HttpOnly; Max-Age=7776000; Path=/; SameSite=lax; Secure'
				]
			]
		});

		expect(relaySessionCookie(response, cookies as unknown as Cookies)).toBe(true);

		expect(set).toEqual([
			['tart_session', 'abc-123', { path: '/', httpOnly: true, sameSite: 'lax', maxAge: 7776000 }]
		]);
	});

	it('relays nothing when the API set no session', () => {
		const { set, cookies } = recordingCookies();

		expect(relaySessionCookie(new Response(null), cookies as unknown as Cookies)).toBe(false);
		expect(set).toEqual([]);
	});
});
