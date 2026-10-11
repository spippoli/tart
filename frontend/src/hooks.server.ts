import { createApiClient } from './lib/api/client';
import { createContentSecurityPolicyHandle } from './lib/server/content-security-policy';
import { createInstanceConfigReader } from './lib/server/instance-config';

/** Where the server side reaches the API: the `api` service of the Compose stack by default. */
const apiUrl = process.env.API_URL || 'http://api:8000';

const readInstanceConfig = createInstanceConfigReader(createApiClient({ baseUrl: apiUrl }));

export const handle = createContentSecurityPolicyHandle(readInstanceConfig);
