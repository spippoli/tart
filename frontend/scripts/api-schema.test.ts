import { readFileSync } from 'node:fs';
import { expect, it } from 'vitest';
import { generateApiTypes, typesFile } from './api-schema.ts';

it('the committed API client types match the OpenAPI schema', async () => {
	const committed = readFileSync(typesFile, 'utf8');

	expect(committed, 'The API client drifted: run pnpm api:generate').toBe(await generateApiTypes());
});
