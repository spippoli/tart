/**
 * A stand-in for the `api` service in the end-to-end tests: it answers
 * `GET /api/config` with a fictional public configuration. Under the `/it-only`
 * prefix, the same configuration enables Italian alone, for a second frontend
 * server that tests a disabled UI language.
 *
 *     node e2e/mock-api.ts [port]
 */
import { readFileSync } from 'node:fs';
import { createServer } from 'node:http';

const config = JSON.parse(readFileSync(new URL('fixtures/config.json', import.meta.url), 'utf8'));
const variants: Record<string, unknown> = {
	'/api/config': config,
	'/it-only/api/config': { ...config, languages: { ...config.languages, ui: ['it'] } }
};

const port = Number(process.argv[2] ?? 8795);
createServer((request, response) => {
	const body = variants[request.url ?? ''];
	if (request.method !== 'GET' || body === undefined) {
		response.writeHead(404).end();
		return;
	}
	response.writeHead(200, { 'Content-Type': 'application/json' }).end(JSON.stringify(body));
}).listen(port);
