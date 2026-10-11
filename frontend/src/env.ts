import { defineEnvVars } from '@sveltejs/kit/env';

export const variables = defineEnvVars({
	API_URL: {
		description:
			'The `api` service as the frontend server reaches it, inside the Compose network; browsers reach the API through Caddy at `/api`.',
		schema: (value) => value || 'http://api:8000'
	}
});
