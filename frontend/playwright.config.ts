import { defineConfig, devices } from '@playwright/test';

const MOCK_API = 'http://localhost:8795';

export default defineConfig({
	testDir: 'e2e',
	testMatch: '**/*.e2e.ts',
	forbidOnly: !!process.env.CI,
	// Started in order: the stand-in API, then the production build against it, then
	// a second server of the same build whose Instance enables Italian only.
	webServer: [
		{ command: 'node e2e/mock-api.ts 8795', url: `${MOCK_API}/api/config` },
		{
			command: 'pnpm build && pnpm preview --port 4273 --strictPort',
			port: 4273,
			env: { API_URL: MOCK_API }
		},
		{
			command: 'pnpm preview --port 4274 --strictPort',
			port: 4274,
			env: { API_URL: `${MOCK_API}/it-only` }
		}
	],
	use: { baseURL: 'http://localhost:4273' },
	projects: [
		{ name: 'desktop', use: { ...devices['Desktop Chrome'] } },
		{ name: 'mobile', use: { ...devices['Pixel 7'] } }
	]
});
